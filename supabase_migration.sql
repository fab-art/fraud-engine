-- Pharmaceutical Counter Verification Schema
-- Supabase SQL Migration Script

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom enums
CREATE TYPE user_role AS ENUM ('trainee', 'officer', 'supervisor', 'compliance');
CREATE TYPE batch_status AS ENUM ('processing', 'pending_review', 'closed');
CREATE TYPE finding_status AS ENUM ('draft', 'escalated', 'approved');

-- Profiles table (links to Supabase auth)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    role user_role NOT NULL DEFAULT 'trainee',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Audit batches table
CREATE TABLE audit_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename TEXT NOT NULL,
    uploaded_by UUID NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
    total_claims INTEGER NOT NULL DEFAULT 0,
    status batch_status NOT NULL DEFAULT 'processing',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Claims table
CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id UUID NOT NULL REFERENCES audit_batches(id) ON DELETE CASCADE,
    paper_code TEXT NOT NULL,
    patient_rama TEXT NOT NULL,
    patient_name TEXT NOT NULL,
    dispensing_date DATE NOT NULL,
    facility_name TEXT NOT NULL,
    prescriber_name TEXT NOT NULL,
    drug_code TEXT NOT NULL,
    insurance_copay NUMERIC(10,2) NOT NULL DEFAULT 0,
    verification_status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Hospital visits table
CREATE TABLE hospital_visits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_batch_id UUID NOT NULL REFERENCES audit_batches(id) ON DELETE CASCADE,
    patient_rama TEXT NOT NULL,
    visit_date DATE NOT NULL,
    facility_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Verification findings table
CREATE TABLE verification_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    rule_triggered TEXT NOT NULL,
    ml_anomaly_score NUMERIC(5,4),
    composite_risk_score INTEGER NOT NULL CHECK (composite_risk_score BETWEEN 0 AND 100),
    deduction_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
    officer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
    supervisor_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    status finding_status NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_audit_batches_uploaded_by ON audit_batches(uploaded_by);
CREATE INDEX idx_audit_batches_status ON audit_batches(status);
CREATE INDEX idx_claims_batch_id ON claims(batch_id);
CREATE INDEX idx_claims_patient_rama ON claims(patient_rama);
CREATE INDEX idx_claims_verification_status ON claims(verification_status);
CREATE INDEX idx_hospital_visits_source_batch_id ON hospital_visits(source_batch_id);
CREATE INDEX idx_hospital_visits_patient_rama ON hospital_visits(patient_rama);
CREATE INDEX idx_verification_findings_claim_id ON verification_findings(claim_id);
CREATE INDEX idx_verification_findings_officer_id ON verification_findings(officer_id);
CREATE INDEX idx_verification_findings_status ON verification_findings(status);

-- Enable Row Level Security on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE hospital_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_findings ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Only authenticated internal staff can access data

-- Profiles policies
CREATE POLICY "Internal staff can view all profiles"
    ON profiles FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Internal staff can insert own profile"
    ON profiles FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Supervisors and compliance can update profiles"
    ON profiles FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() 
            AND role IN ('supervisor', 'compliance')
        )
    );

-- Audit batches policies
CREATE POLICY "Internal staff can view audit batches"
    ON audit_batches FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Internal staff can create audit batches"
    ON audit_batches FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = uploaded_by);

CREATE POLICY "Officers and above can update audit batches"
    ON audit_batches FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() 
            AND role IN ('officer', 'supervisor', 'compliance')
        )
    );

-- Claims policies
CREATE POLICY "Internal staff can view claims"
    ON claims FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Officers and above can insert claims"
    ON claims FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() 
            AND role IN ('officer', 'supervisor', 'compliance')
        )
    );

CREATE POLICY "Officers and above can update claims"
    ON claims FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() 
            AND role IN ('officer', 'supervisor', 'compliance')
        )
    );

-- Hospital visits policies
CREATE POLICY "Internal staff can view hospital visits"
    ON hospital_visits FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Officers and above can insert hospital visits"
    ON hospital_visits FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() 
            AND role IN ('officer', 'supervisor', 'compliance')
        )
    );

-- Verification findings policies
CREATE POLICY "Internal staff can view verification findings"
    ON verification_findings FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Officers and supervisors can insert verification findings"
    ON verification_findings FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() 
            AND role IN ('officer', 'supervisor', 'compliance')
        )
        AND officer_id = auth.uid()
    );

CREATE POLICY "Officers can update their own findings, supervisors and compliance can update all"
    ON verification_findings FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() 
            AND role IN ('supervisor', 'compliance')
        )
        OR officer_id = auth.uid()
    );

-- Function to automatically create profile trigger
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, role)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'full_name', 'Unknown User'),
        COALESCE((NEW.raw_user_meta_data->>'role')::user_role, 'trainee')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to automatically create profile on user signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;
