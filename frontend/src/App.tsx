import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Upload, FileCheck, Activity } from 'lucide-react'

function Sidebar() {
  const location = useLocation()
  
  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/ingest', label: 'Ingestion Hub', icon: Upload },
    { path: '/workbench', label: 'CVL Workbench', icon: FileCheck },
  ]
  
  return (
    <aside className="w-64 bg-gray-900 border-r border-gray-800 min-h-screen flex flex-col">
      <div className="p-6 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Activity className="w-6 h-6 text-blue-500" />
          PharmaScan CVL
        </h1>
      </div>
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
    </aside>
  )
}

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-gray-950">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">
        {children}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/workbench" element={<WorkbenchPlaceholder />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  )
}

function Dashboard() {
  return (
    <div>
      <h2 className="text-3xl font-bold text-white mb-8">Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Audits Pending"
          value="23"
          description="Awaiting review"
          trend="+5 from last week"
        />
        <MetricCard
          title="High Risk Claims"
          value="12"
          description="Requires immediate attention"
          trend="+2 from last week"
          variant="danger"
        />
        <MetricCard
          title="Total Processed"
          value="1,847"
          description="This month"
          trend="+12% from last month"
        />
        <MetricCard
          title="Recovery Rate"
          value="94.2%"
          description="Successful recoveries"
          trend="+1.3% from last month"
          variant="success"
        />
      </div>
    </div>
  )
}

function MetricCard({ 
  title, 
  value, 
  description, 
  trend, 
  variant = 'default' 
}: { 
  title: string
  value: string
  description: string
  trend: string
  variant?: 'default' | 'success' | 'danger'
}) {
  const variantClasses = {
    default: 'border-gray-800 bg-gray-900',
    success: 'border-green-800 bg-green-900/20',
    danger: 'border-red-800 bg-red-900/20',
  }
  
  const trendColor = trend.startsWith('+') ? 'text-green-400' : 'text-red-400'
  
  return (
    <div className={`p-6 rounded-xl border ${variantClasses[variant]}`}>
      <h3 className="text-gray-400 text-sm font-medium mb-2">{title}</h3>
      <p className="text-3xl font-bold text-white mb-2">{value}</p>
      <p className="text-gray-500 text-sm mb-3">{description}</p>
      <p className={`text-xs ${trendColor}`}>{trend}</p>
    </div>
  )
}

function IngestPage() {
  return (
    <div>
      <h2 className="text-3xl font-bold text-white mb-8">Ingestion Hub</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <PharmacyUploadZone />
        <FacilityUploadZone />
      </div>
    </div>
  )
}

function PharmacyUploadZone() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setMessage(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setMessage({ type: 'error', text: 'Please select a file first' })
      return
    }

    setLoading(true)
    setMessage(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/ingest/pharmacy', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (response.ok) {
        setMessage({ type: 'success', text: `Successfully uploaded! Batch ID: ${data.batch_id}, Records: ${data.inserted_count}` })
        setFile(null)
      } else {
        setMessage({ type: 'error', text: data.detail || 'Upload failed' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error. Make sure the backend is running.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h3 className="text-xl font-semibold text-white mb-4">Upload Pharmacy Invoice Batch</h3>
      <p className="text-gray-400 text-sm mb-6">
        Upload CSV or Excel files with columns: paper_code, patient_rama, patient_name, dispensing_date, facility_name, prescriber_name, drug_code, insurance_copay
      </p>
      
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-300 mb-2">Select File</label>
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
        />
      </div>

      {file && (
        <div className="mb-6 p-4 bg-gray-800 rounded-lg">
          <p className="text-gray-300 text-sm">Selected: <span className="text-white font-medium">{file.name}</span></p>
          <p className="text-gray-500 text-xs">{(file.size / 1024).toFixed(2)} KB</p>
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={loading || !file}
        className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
          loading || !file
            ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700'
        }`}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Uploading...
          </span>
        ) : (
          'Upload Pharmacy Data'
        )}
      </button>

      {message && (
        <div className={`mt-4 p-4 rounded-lg ${
          message.type === 'success' ? 'bg-green-900/30 border border-green-800' : 'bg-red-900/30 border border-red-800'
        }`}>
          <p className={`text-sm ${message.type === 'success' ? 'text-green-400' : 'text-red-400'}`}>
            {message.text}
          </p>
        </div>
      )}
    </div>
  )
}

function FacilityUploadZone() {
  const [file, setFile] = useState<File | null>(null)
  const [batchId, setBatchId] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setMessage(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setMessage({ type: 'error', text: 'Please select a file first' })
      return
    }

    if (!batchId) {
      setMessage({ type: 'error', text: 'Please enter a batch ID' })
      return
    }

    setLoading(true)
    setMessage(null)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('batch_id', batchId)

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/v1/ingest/facility?batch_id=${batchId}`, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (response.ok) {
        setMessage({ type: 'success', text: `Successfully uploaded! Records: ${data.inserted_count}` })
        setFile(null)
        setBatchId('')
      } else {
        setMessage({ type: 'error', text: data.detail || 'Upload failed' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error. Make sure the backend is running.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h3 className="text-xl font-semibold text-white mb-4">Upload Hospital/Clinic Visit Records</h3>
      <p className="text-gray-400 text-sm mb-6">
        Upload CSV or Excel files with columns: patient_rama, visit_date, facility_name
      </p>
      
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-300 mb-2">Batch ID (UUID)</label>
        <input
          type="text"
          value={batchId}
          onChange={(e) => setBatchId(e.target.value)}
          placeholder="Enter batch ID from pharmacy upload"
          className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-300 mb-2">Select File</label>
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
        />
      </div>

      {file && (
        <div className="mb-6 p-4 bg-gray-800 rounded-lg">
          <p className="text-gray-300 text-sm">Selected: <span className="text-white font-medium">{file.name}</span></p>
          <p className="text-gray-500 text-xs">{(file.size / 1024).toFixed(2)} KB</p>
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={loading || !file || !batchId}
        className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
          loading || !file || !batchId
            ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700'
        }`}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Uploading...
          </span>
        ) : (
          'Upload Facility Data'
        )}
      </button>

      {message && (
        <div className={`mt-4 p-4 rounded-lg ${
          message.type === 'success' ? 'bg-green-900/30 border border-green-800' : 'bg-red-900/30 border border-red-800'
        }`}>
          <p className={`text-sm ${message.type === 'success' ? 'text-green-400' : 'text-red-400'}`}>
            {message.text}
          </p>
        </div>
      )}
    </div>
  )
}

function WorkbenchPlaceholder() {
  return (
    <div className="flex items-center justify-center h-96">
      <div className="text-center">
        <FileCheck className="w-16 h-16 text-gray-700 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-400 mb-2">CVL Workbench</h2>
        <p className="text-gray-500">Coming soon - Claim verification workspace</p>
      </div>
    </div>
  )
}
