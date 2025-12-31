import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import { 
  Loader2, AlertCircle, Plus, Upload, 
  Trash2, Download, Key, FileText, Shield, FileCheck 
} from 'lucide-react'

interface Certificate {
  id: number
  name: string
  description?: string
  cert_type: string
  cert_filename?: string
  csr_subject?: string
  csr_key_size?: number
  created_at: string
  updated_at: string
  created_by?: string
}

export default function CertificateSettings() {
  const queryClient = useQueryClient()
  const [showCSRForm, setShowCSRForm] = useState(false)
  const [showUploadForm, setShowUploadForm] = useState(false)

  // CSR Form state
  const [csrFormData, setCsrFormData] = useState({
    name: '',
    description: '',
    common_name: '',
    organization: '',
    organizational_unit: '',
    locality: '',
    state: '',
    country: 'US',
    email: '',
    key_size: 2048,
  })

  // Upload form state
  const [uploadFormData, setUploadFormData] = useState({
    name: '',
    description: '',
    cert_type: 'client_cert',
    certFile: null as File | null,
  })

  // Fetch certificates
  const { data: certificatesData, isLoading, error } = useQuery({
    queryKey: ['certificates'],
    queryFn: async () => {
      const response = await apiClient.getCertificates()
      return response.data.certificates as Certificate[]
    },
  })

  // Generate CSR mutation
  const generateCSRMutation = useMutation({
    mutationFn: async () => {
      return apiClient.generateCSR(csrFormData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      setShowCSRForm(false)
      setCsrFormData({
        name: '',
        description: '',
        common_name: '',
        organization: '',
        organizational_unit: '',
        locality: '',
        state: '',
        country: 'US',
        email: '',
        key_size: 2048,
      })
      alert('CSR generated successfully! Download the CSR and submit it to your CA for signing.')
    },
    onError: (error: any) => {
      alert(`Error generating CSR: ${error.response?.data?.detail || error.message}`)
    },
  })

  // Upload certificate mutation
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadFormData.certFile) throw new Error('Please select a file')
      return apiClient.uploadGlobalCertificate(
        uploadFormData.name,
        uploadFormData.description || null,
        uploadFormData.cert_type,
        uploadFormData.certFile
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      setShowUploadForm(false)
      setUploadFormData({
        name: '',
        description: '',
        cert_type: 'client_cert',
        certFile: null,
      })
      alert('Certificate uploaded successfully')
    },
    onError: (error: any) => {
      alert(`Error uploading certificate: ${error.response?.data?.detail || error.message}`)
    },
  })

  // Delete certificate mutation
  const deleteMutation = useMutation({
    mutationFn: async (certificateId: number) => {
      return apiClient.deleteCertificateById(certificateId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      alert('Certificate deleted successfully')
    },
    onError: (error: any) => {
      alert(`Error deleting certificate: ${error.response?.data?.detail || error.message}`)
    },
  })

  // Download CSR mutation
  const downloadCSRMutation = useMutation({
    mutationFn: async (certificateId: number) => {
      const response = await apiClient.downloadCSR(certificateId)
      return { data: response.data, certificateId }
    },
    onSuccess: async (result) => {
      // Get certificate name for filename
      const cert = certificatesData?.find(c => c.id === result.certificateId)
      const filename = cert?.name || `certificate-${result.certificateId}`
      
      // Create blob and download
      const blob = new Blob([result.data], { type: 'application/x-pem-file' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${filename}.csr`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    },
    onError: (error: any) => {
      alert(`Error downloading CSR: ${error.response?.data?.detail || error.message}`)
    },
  })

  const getCertTypeIcon = (certType: string) => {
    switch (certType) {
      case 'client_cert':
        return <FileCheck className="h-5 w-5 text-blue-500" />
      case 'client_key':
        return <Key className="h-5 w-5 text-yellow-500" />
      case 'ca_cert':
        return <Shield className="h-5 w-5 text-green-500" />
      case 'csr':
        return <FileText className="h-5 w-5 text-purple-500" />
      default:
        return <FileText className="h-5 w-5 text-gray-500" />
    }
  }

  const getCertTypeLabel = (certType: string) => {
    switch (certType) {
      case 'client_cert':
        return 'Client Certificate'
      case 'client_key':
        return 'Private Key'
      case 'ca_cert':
        return 'Root/CA Certificate'
      case 'csr':
        return 'Certificate Signing Request'
      default:
        return certType
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        <span className="ml-2 text-gray-600">Loading certificates...</span>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Certificate Management</h2>
        <div className="flex space-x-2">
          <button
            onClick={() => setShowUploadForm(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center space-x-2"
          >
            <Upload className="h-4 w-4" />
            <span>Upload Certificate</span>
          </button>
          <button
            onClick={() => setShowCSRForm(true)}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 flex items-center space-x-2"
          >
            <Plus className="h-4 w-4" />
            <span>Generate CSR</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex items-center space-x-2 text-red-800">
            <AlertCircle className="h-5 w-5" />
            <span>Error loading certificates: {(error as any).message}</span>
          </div>
        </div>
      )}

      {/* CSR Generation Form */}
      {showCSRForm && (
        <div className="border rounded-lg p-6 mb-6 bg-gray-50">
          <h3 className="text-lg font-semibold mb-4">Generate Certificate Signing Request (CSR)</h3>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Certificate Name *
                </label>
                <input
                  type="text"
                  value={csrFormData.name}
                  onChange={(e) => setCsrFormData({ ...csrFormData, name: e.target.value })}
                  placeholder="clarion-pxgrid-client"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Common Name (CN) *
                </label>
                <input
                  type="text"
                  value={csrFormData.common_name}
                  onChange={(e) => setCsrFormData({ ...csrFormData, common_name: e.target.value })}
                  placeholder="clarion.example.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Organization (O)
                </label>
                <input
                  type="text"
                  value={csrFormData.organization}
                  onChange={(e) => setCsrFormData({ ...csrFormData, organization: e.target.value })}
                  placeholder="Your Organization"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Organizational Unit (OU)
                </label>
                <input
                  type="text"
                  value={csrFormData.organizational_unit}
                  onChange={(e) => setCsrFormData({ ...csrFormData, organizational_unit: e.target.value })}
                  placeholder="IT Department"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Locality (L)
                </label>
                <input
                  type="text"
                  value={csrFormData.locality}
                  onChange={(e) => setCsrFormData({ ...csrFormData, locality: e.target.value })}
                  placeholder="City"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  State/Province (ST)
                </label>
                <input
                  type="text"
                  value={csrFormData.state}
                  onChange={(e) => setCsrFormData({ ...csrFormData, state: e.target.value })}
                  placeholder="State"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Country (C)
                </label>
                <input
                  type="text"
                  value={csrFormData.country}
                  onChange={(e) => setCsrFormData({ ...csrFormData, country: e.target.value })}
                  placeholder="US"
                  maxLength={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={csrFormData.email}
                  onChange={(e) => setCsrFormData({ ...csrFormData, email: e.target.value })}
                  placeholder="admin@example.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <input
                type="text"
                value={csrFormData.description}
                onChange={(e) => setCsrFormData({ ...csrFormData, description: e.target.value })}
                placeholder="Optional description"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Key Size (bits)
              </label>
              <select
                value={csrFormData.key_size}
                onChange={(e) => setCsrFormData({ ...csrFormData, key_size: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={2048}>2048 (Recommended)</option>
                <option value={4096}>4096 (Higher Security)</option>
              </select>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => generateCSRMutation.mutate()}
                disabled={generateCSRMutation.isPending || !csrFormData.name || !csrFormData.common_name}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center space-x-2"
              >
                {generateCSRMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                <span>Generate CSR</span>
              </button>
              <button
                onClick={() => {
                  setShowCSRForm(false)
                  setCsrFormData({
                    name: '',
                    description: '',
                    common_name: '',
                    organization: '',
                    organizational_unit: '',
                    locality: '',
                    state: '',
                    country: 'US',
                    email: '',
                    key_size: 2048,
                  })
                }}
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Form */}
      {showUploadForm && (
        <div className="border rounded-lg p-6 mb-6 bg-gray-50">
          <h3 className="text-lg font-semibold mb-4">Upload Certificate</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Certificate Name *
              </label>
              <input
                type="text"
                value={uploadFormData.name}
                onChange={(e) => setUploadFormData({ ...uploadFormData, name: e.target.value })}
                placeholder="my-certificate"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Certificate Type *
              </label>
              <select
                value={uploadFormData.cert_type}
                onChange={(e) => setUploadFormData({ ...uploadFormData, cert_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="client_cert">Client Certificate</option>
                <option value="client_key">Private Key</option>
                <option value="ca_cert">Root/CA Certificate</option>
              </select>
              {uploadFormData.cert_type === 'client_cert' && (
                <p className="text-xs text-gray-500 mt-1">
                  Device/Client certificate for pxGrid (PEM format - Base64 encoded). This identifies the Clarion pxGrid client to ISE, not a user certificate.
                </p>
              )}
              {uploadFormData.cert_type === 'client_key' && (
                <p className="text-xs text-gray-500 mt-1">
                  Private key matching the client certificate (PEM format - Base64 encoded). Must be in unencrypted PEM format.
                </p>
              )}
              {uploadFormData.cert_type === 'ca_cert' && (
                <p className="text-xs text-gray-500 mt-1">
                  Root CA certificate that signed the ISE server certificate (PEM format - Base64 encoded). Used to verify ISE's SSL certificate.
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <input
                type="text"
                value={uploadFormData.description}
                onChange={(e) => setUploadFormData({ ...uploadFormData, description: e.target.value })}
                placeholder="Optional description"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Certificate File *
              </label>
              <input
                type="file"
                onChange={(e) => setUploadFormData({ ...uploadFormData, certFile: e.target.files?.[0] || null })}
                accept=".pem,.crt,.key,.cer"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Certificate must be in PEM format (Base64 encoded, not DER binary). File should contain BEGIN/END markers.
              </p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => uploadMutation.mutate()}
                disabled={uploadMutation.isPending || !uploadFormData.name || !uploadFormData.certFile}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
              >
                {uploadMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                <span>Upload</span>
              </button>
              <button
                onClick={() => {
                  setShowUploadForm(false)
                  setUploadFormData({
                    name: '',
                    description: '',
                    cert_type: 'client_cert',
                    certFile: null,
                  })
                }}
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Certificates List */}
      {certificatesData && certificatesData.length > 0 ? (
        <div className="space-y-4">
          {certificatesData.map((cert) => (
            <div key={cert.id} className="border rounded-lg p-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {getCertTypeIcon(cert.cert_type)}
                  <div>
                    <h3 className="font-semibold">{cert.name}</h3>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <span>{getCertTypeLabel(cert.cert_type)}</span>
                      {cert.csr_key_size && <span>Key Size: {cert.csr_key_size} bits</span>}
                      {cert.cert_filename && <span>File: {cert.cert_filename}</span>}
                      <span>Created: {new Date(cert.created_at).toLocaleDateString()}</span>
                    </div>
                    {cert.description && (
                      <p className="text-sm text-gray-500 mt-1">{cert.description}</p>
                    )}
                    {cert.csr_subject && (
                      <p className="text-xs text-gray-400 mt-1">Subject: {cert.csr_subject}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {cert.cert_type === 'csr' && (
                    <button
                      onClick={() => downloadCSRMutation.mutate(cert.id)}
                      disabled={downloadCSRMutation.isPending}
                      className="px-3 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-1"
                    >
                      <Download className="h-4 w-4" />
                      <span>Download CSR</span>
                    </button>
                  )}
                  <button
                    onClick={() => {
                      if (confirm(`Delete certificate "${cert.name}"?`)) {
                        deleteMutation.mutate(cert.id)
                      }
                    }}
                    disabled={deleteMutation.isPending}
                    className="px-3 py-1 bg-red-600 text-white text-sm rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center space-x-1"
                  >
                    <Trash2 className="h-4 w-4" />
                    <span>Delete</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500">
          <FileText className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <p>No certificates found. Generate a CSR or upload a certificate to get started.</p>
        </div>
      )}
    </div>
  )
}

