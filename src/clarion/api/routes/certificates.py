"""
Certificate Management API Routes

Endpoints for managing certificates, including CSR generation, certificate upload,
and certificate assignment to connectors.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
import json
from datetime import datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import base64

from clarion.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Request/Response Models ==========

class CSRGenerateRequest(BaseModel):
    """Request to generate a CSR."""
    name: str = Field(..., description="Certificate name (must be unique)")
    description: Optional[str] = Field(None, description="Optional description")
    common_name: str = Field(..., description="Common Name (CN) for the certificate")
    organization: Optional[str] = Field(None, description="Organization (O)")
    organizational_unit: Optional[str] = Field(None, description="Organizational Unit (OU)")
    locality: Optional[str] = Field(None, description="Locality (L)")
    state: Optional[str] = Field(None, description="State or Province (ST)")
    country: Optional[str] = Field(None, description="Country Code (C), e.g., 'US'")
    email: Optional[str] = Field(None, description="Email address")
    key_size: int = Field(2048, description="Key size in bits (2048 or 4096)", ge=2048, le=4096)


class CertificateUploadRequest(BaseModel):
    """Request to upload a certificate."""
    name: str = Field(..., description="Certificate name (must be unique)")
    description: Optional[str] = Field(None, description="Optional description")
    cert_type: str = Field(..., description="Certificate type: client_cert, client_key, ca_cert")


class CertificateResponse(BaseModel):
    """Certificate response."""
    id: int
    name: str
    description: Optional[str]
    cert_type: str
    cert_filename: Optional[str]
    csr_subject: Optional[str]
    csr_key_size: Optional[int]
    created_at: str
    updated_at: str
    created_by: Optional[str]


class CertificateListResponse(BaseModel):
    """List of certificates."""
    certificates: List[CertificateResponse]


class CertificateDetailResponse(BaseModel):
    """Certificate detail response (includes CSR text for download)."""
    id: int
    name: str
    description: Optional[str]
    cert_type: str
    cert_filename: Optional[str]
    csr_subject: Optional[str]
    csr_key_size: Optional[int]
    created_at: str
    updated_at: str
    created_by: Optional[str]
    csr_text: Optional[str] = Field(None, description="CSR text in PEM format (only for CSR type)")


class CertificateAssignRequest(BaseModel):
    """Request to assign a certificate to a connector."""
    certificate_id: int = Field(..., description="Certificate ID to assign")
    reference_type: str = Field(..., description="Reference type: client_cert, client_key, ca_cert")


# ========== Certificate Management Endpoints ==========

@router.post("/certificates/csr/generate", response_model=CertificateDetailResponse)
async def generate_csr(request: CSRGenerateRequest):
    """
    Generate a Certificate Signing Request (CSR) and private key.
    
    Returns the CSR in PEM format and stores the private key securely.
    The CSR can be downloaded and submitted to a CA for signing.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if certificate name already exists
        cursor = conn.execute("""
            SELECT id FROM certificates WHERE name = ?
        """, (request.name,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Certificate with name '{request.name}' already exists"
            )
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=request.key_size,
        )
        
        # Build subject
        subject_components = []
        if request.country:
            subject_components.append(x509.NameAttribute(NameOID.COUNTRY_NAME, request.country))
        if request.state:
            subject_components.append(x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, request.state))
        if request.locality:
            subject_components.append(x509.NameAttribute(NameOID.LOCALITY_NAME, request.locality))
        if request.organization:
            subject_components.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, request.organization))
        if request.organizational_unit:
            subject_components.append(x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, request.organizational_unit))
        subject_components.append(x509.NameAttribute(NameOID.COMMON_NAME, request.common_name))
        if request.email:
            subject_components.append(x509.NameAttribute(NameOID.EMAIL_ADDRESS, request.email))
        
        subject = x509.Name(subject_components)
        
        # Create CSR
        csr = x509.CertificateSigningRequestBuilder().subject_name(subject).sign(
            private_key, hashes.SHA256()
        )
        
        # Serialize CSR and private key to PEM format
        csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Store private key as a certificate entry (cert_type='client_key')
        key_name = f"{request.name}-key"
        conn.execute("""
            INSERT INTO certificates (
                name, description, cert_type, cert_data, cert_filename,
                csr_key_size, created_at, updated_at, created_by
            ) VALUES (?, ?, 'client_key', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'system')
        """, (
            key_name,
            f"Private key for {request.name}",
            private_key_pem,
            f"{request.name}.key",
            request.key_size,
        ))
        
        # Store CSR as a certificate entry
        csr_subject = subject.rfc4514_string()
        conn.execute("""
            INSERT INTO certificates (
                name, description, cert_type, cert_data, cert_filename,
                csr_subject, csr_key_size, created_at, updated_at, created_by
            ) VALUES (?, ?, 'csr', ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'system')
        """, (
            request.name,
            request.description,
            csr_pem.encode('utf-8'),
            f"{request.name}.csr",
            csr_subject,
            request.key_size,
        ))
        
        conn.commit()
        
        # Get the CSR certificate ID
        cursor = conn.execute("""
            SELECT id FROM certificates WHERE name = ? AND cert_type = 'csr'
        """, (request.name,))
        csr_row = cursor.fetchone()
        
        if not csr_row:
            raise HTTPException(status_code=500, detail="Failed to retrieve generated CSR")
        
        return CertificateDetailResponse(
            id=csr_row['id'],
            name=request.name,
            description=request.description,
            cert_type='csr',
            cert_filename=f"{request.name}.csr",
            csr_subject=csr_subject,
            csr_key_size=request.key_size,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            created_by='system',
            csr_text=csr_pem,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating CSR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/certificates/upload", response_model=CertificateResponse)
async def upload_certificate(
    name: str = Form(..., description="Certificate name (must be unique)"),
    description: Optional[str] = Form(None, description="Optional description"),
    cert_type: str = Form(..., description="Certificate type: client_cert, client_key, ca_cert"),
    cert_file: UploadFile = File(..., description="Certificate file"),
):
    """
    Upload a certificate file.
    
    Supported certificate types:
    - client_cert: Client certificate (PEM format - Base64 encoded with BEGIN/END markers)
      For pxGrid, this should be a device/client certificate, not a user certificate.
      Common extensions: .crt, .pem, .cer
    - client_key: Private key (PEM format - Base64 encoded with BEGIN/END markers)
      Must match the client certificate. Common extensions: .key, .pem
    - ca_cert: CA/Root certificate (PEM format - Base64 encoded with BEGIN/END markers)
      Root CA certificate that signed the server certificate. Common extensions: .crt, .pem, .cer
    
    Note: Certificates must be in PEM format (Base64), not DER (binary) format.
    """
    if cert_type not in ['client_cert', 'client_key', 'ca_cert']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid certificate type: {cert_type}. Must be one of: client_cert, client_key, ca_cert"
        )
    
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if certificate name already exists
        cursor = conn.execute("""
            SELECT id FROM certificates WHERE name = ?
        """, (name,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Certificate with name '{name}' already exists"
            )
        
        # Read certificate file
        cert_data = await cert_file.read()
        
        # Store certificate
        conn.execute("""
            INSERT INTO certificates (
                name, description, cert_type, cert_data, cert_filename,
                created_at, updated_at, created_by
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'user')
        """, (name, description, cert_type, cert_data, cert_file.filename))
        conn.commit()
        
        # Get the inserted certificate
        cursor = conn.execute("""
            SELECT * FROM certificates WHERE name = ?
        """, (name,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=500, detail="Failed to retrieve uploaded certificate")
        
        return CertificateResponse(
            id=row['id'],
            name=row['name'],
            description=row['description'] if row['description'] else None,
            cert_type=row['cert_type'],
            cert_filename=row['cert_filename'] if row['cert_filename'] else None,
            csr_subject=row['csr_subject'] if row['csr_subject'] else None,
            csr_key_size=row['csr_key_size'] if row['csr_key_size'] else None,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            created_by=row['created_by'] if row['created_by'] else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading certificate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/certificates", response_model=CertificateListResponse)
async def list_certificates():
    """
    List all certificates.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute("""
            SELECT * FROM certificates ORDER BY created_at DESC
        """)
        
        certificates = []
        for row in cursor.fetchall():
            certificates.append(CertificateResponse(
                id=row['id'],
                name=row['name'],
                description=row['description'] if row['description'] else None,
                cert_type=row['cert_type'],
                cert_filename=row['cert_filename'] if row['cert_filename'] else None,
                csr_subject=row['csr_subject'] if row['csr_subject'] else None,
                csr_key_size=row['csr_key_size'] if row['csr_key_size'] else None,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                created_by=row['created_by'] if row['created_by'] else None,
            ))
        
        return CertificateListResponse(certificates=certificates)
        
    except Exception as e:
        logger.error(f"Error listing certificates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/certificates/{certificate_id}", response_model=CertificateDetailResponse)
async def get_certificate(certificate_id: int):
    """
    Get certificate details, including CSR text if it's a CSR.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute("""
            SELECT * FROM certificates WHERE id = ?
        """, (certificate_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Certificate {certificate_id} not found"
            )
        
        csr_text = None
        if row['cert_type'] == 'csr' and row['cert_data']:
            csr_text = row['cert_data'].decode('utf-8')
        
        return CertificateDetailResponse(
            id=row['id'],
            name=row['name'],
            description=row['description'] if row['description'] else None,
            cert_type=row['cert_type'],
            cert_filename=row['cert_filename'] if row['cert_filename'] else None,
            csr_subject=row['csr_subject'] if row['csr_subject'] else None,
            csr_key_size=row['csr_key_size'] if row['csr_key_size'] else None,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            created_by=row['created_by'] if row['created_by'] else None,
            csr_text=csr_text,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting certificate {certificate_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/certificates/{certificate_id}")
async def delete_certificate(certificate_id: int):
    """
    Delete a certificate.
    
    Note: This will also remove all connector references to this certificate.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute("""
            DELETE FROM certificates WHERE id = ?
        """, (certificate_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Certificate {certificate_id} not found"
            )
        
        return {
            "status": "success",
            "message": f"Certificate {certificate_id} deleted successfully",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting certificate {certificate_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/certificates/{certificate_id}/download-csr")
async def download_csr(certificate_id: int):
    """
    Download CSR in PEM format.
    
    Returns the CSR as a text file for submission to a CA.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute("""
            SELECT name, cert_data FROM certificates WHERE id = ? AND cert_type = 'csr'
        """, (certificate_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"CSR {certificate_id} not found"
            )
        
        from fastapi.responses import Response
        return Response(
            content=row['cert_data'].decode('utf-8'),
            media_type="application/x-pem-file",
            headers={
                "Content-Disposition": f'attachment; filename="{row["name"]}.csr"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading CSR {certificate_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connectors/{connector_id}/certificates/assign", response_model=Dict[str, Any])
async def assign_certificate_to_connector(
    connector_id: str,
    request: CertificateAssignRequest,
):
    """
    Assign a certificate to a connector.
    
    This creates a reference from the connector to the certificate,
    allowing the connector to use the certificate for authentication.
    
    If the connector doesn't exist yet, it will be created with default values.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Define available connector types (must match connectors.py)
        connector_definitions = {
            'ise_ers': {
                'name': 'ISE ERS API',
                'type': 'ise_ers',
                'description': 'Cisco ISE ERS API connector for policy deployment and configuration sync'
            },
            'ise_pxgrid': {
                'name': 'ISE pxGrid',
                'type': 'ise_pxgrid',
                'description': 'Cisco ISE pxGrid connector for real-time session and endpoint events'
            },
            'ad': {
                'name': 'Active Directory',
                'type': 'ad',
                'description': 'LDAP connector for users, groups, and device information'
            },
        }
        
        # Validate connector_id
        if connector_id not in connector_definitions:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown connector: {connector_id}"
            )
        
        definition = connector_definitions[connector_id]
        
        # Ensure connector exists (create if it doesn't)
        cursor = conn.execute("""
            SELECT connector_id FROM connectors WHERE connector_id = ?
        """, (connector_id,))
        if not cursor.fetchone():
            # Create connector with default values
            conn.execute("""
                INSERT INTO connectors (
                    connector_id, name, type, enabled, status, description,
                    created_at, updated_at
                ) VALUES (?, ?, ?, 0, 'disabled', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (connector_id, definition['name'], definition['type'], definition['description']))
            conn.commit()
        
        # Verify certificate exists
        cert_cursor = conn.execute("""
            SELECT id, cert_type FROM certificates WHERE id = ?
        """, (request.certificate_id,))
        cert_row = cert_cursor.fetchone()
        
        if not cert_row:
            raise HTTPException(
                status_code=404,
                detail=f"Certificate {request.certificate_id} not found"
            )
        
        # Verify reference type matches certificate type (with some flexibility)
        valid_combinations = {
            'client_cert': ['client_cert'],
            'client_key': ['client_key'],
            'ca_cert': ['ca_cert'],
            'csr': [],  # CSR cannot be assigned (must be signed first)
        }
        
        if request.reference_type not in valid_combinations.get(cert_row['cert_type'], []):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot assign certificate type '{cert_row['cert_type']}' as '{request.reference_type}'"
            )
        
        # Delete existing reference of this type for this connector
        conn.execute("""
            DELETE FROM certificate_connector_references
            WHERE connector_id = ? AND reference_type = ?
        """, (connector_id, request.reference_type))
        
        # Create new reference
        conn.execute("""
            INSERT INTO certificate_connector_references (
                certificate_id, connector_id, reference_type, created_at
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (request.certificate_id, connector_id, request.reference_type))
        conn.commit()
        
        return {
            "status": "success",
            "message": f"Certificate {request.certificate_id} assigned to connector {connector_id} as {request.reference_type}",
            "connector_id": connector_id,
            "certificate_id": request.certificate_id,
            "reference_type": request.reference_type,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning certificate to connector: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/connectors/{connector_id}/certificates/{reference_type}")
async def unassign_certificate_from_connector(
    connector_id: str,
    reference_type: str,
):
    """
    Remove a certificate assignment from a connector.
    """
    if reference_type not in ['client_cert', 'client_key', 'ca_cert']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reference type: {reference_type}"
        )
    
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute("""
            DELETE FROM certificate_connector_references
            WHERE connector_id = ? AND reference_type = ?
        """, (connector_id, reference_type))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No {reference_type} certificate assigned to connector {connector_id}"
            )
        
        return {
            "status": "success",
            "message": f"Certificate {reference_type} unassigned from connector {connector_id}",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unassigning certificate from connector: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connectors/{connector_id}/certificates")
async def get_connector_certificates(connector_id: str):
    """
    Get certificates assigned to a connector.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute("""
            SELECT 
                c.id, c.name, c.description, c.cert_type, c.cert_filename,
                c.csr_subject, c.csr_key_size, c.created_at, c.updated_at, c.created_by,
                r.reference_type
            FROM certificates c
            INNER JOIN certificate_connector_references r ON c.id = r.certificate_id
            WHERE r.connector_id = ?
        """, (connector_id,))
        
        certificates = {}
        for row in cursor.fetchall():
            ref_type = row['reference_type']
            certificates[ref_type] = {
                "certificate_id": row['id'],
                "name": row['name'],
                "description": row['description'] if row['description'] else None,
                "cert_type": row['cert_type'],
                "cert_filename": row['cert_filename'] if row['cert_filename'] else None,
                "created_at": row['created_at'],
            }
        
        return {
            "connector_id": connector_id,
            "certificates": certificates,
        }
        
    except Exception as e:
        logger.error(f"Error getting connector certificates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

