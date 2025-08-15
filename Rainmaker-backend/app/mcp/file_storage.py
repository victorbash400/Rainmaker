"""
File Storage MCP server for AWS S3 operations
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
import httpx
import base64
from mcp.server import Server
from mcp.types import Tool, TextContent, CallToolResult

from app.core.config import settings

logger = structlog.get_logger(__name__)


class FileStorageMCP:
    """
    MCP server for file storage operations using AWS S3
    """
    
    def __init__(self):
        self.server = Server("file-storage")
        self.aws_access_key = settings.AWS_ACCESS_KEY_ID
        self.aws_secret_key = settings.AWS_SECRET_ACCESS_KEY.get_secret_value() if settings.AWS_SECRET_ACCESS_KEY else None
        self.aws_region = settings.AWS_REGION
        self.s3_bucket = settings.AWS_S3_BUCKET
        
        # Initialize S3 client if credentials are available
        self.s3_client = None
        self._initialize_s3_client()
        
        # Register MCP tools
        self._register_tools()
    
    def _initialize_s3_client(self):
        """Initialize AWS S3 client"""
        try:
            if self.aws_access_key and self.aws_secret_key:
                import boto3
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                logger.info("AWS S3 client initialized successfully")
            else:
                logger.warning("AWS credentials not configured, using mock storage")
        except Exception as e:
            logger.warning("Failed to initialize AWS S3 client", error=str(e))
            self.s3_client = None
    
    def _register_tools(self):
        """Register MCP tools for file storage functionality"""
        
        @self.server.call_tool()
        async def upload_file(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Upload a file to S3 storage
            
            Args:
                file_name: Name of the file
                file_content: Base64 encoded file content
                content_type: MIME type of the file (optional)
                folder: Folder path in S3 (optional)
                public: Whether the file should be publicly accessible (default: false)
            """
            try:
                file_name = arguments.get("file_name")
                file_content = arguments.get("file_content")
                content_type = arguments.get("content_type", "application/octet-stream")
                folder = arguments.get("folder", "")
                public = arguments.get("public", False)
                
                if not file_name or not file_content:
                    raise ValueError("file_name and file_content are required")
                
                # Upload the file
                result = await self._upload_file(
                    file_name=file_name,
                    file_content=file_content,
                    content_type=content_type,
                    folder=folder,
                    public=public
                )
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("File upload failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"File upload failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def download_file(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Download a file from S3 storage
            
            Args:
                file_key: S3 key of the file to download
                return_content: Whether to return file content (default: false, returns URL instead)
            """
            try:
                file_key = arguments.get("file_key")
                return_content = arguments.get("return_content", False)
                
                if not file_key:
                    raise ValueError("file_key is required")
                
                # Download the file
                result = await self._download_file(file_key, return_content)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("File download failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"File download failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def delete_file(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Delete a file from S3 storage
            
            Args:
                file_key: S3 key of the file to delete
            """
            try:
                file_key = arguments.get("file_key")
                
                if not file_key:
                    raise ValueError("file_key is required")
                
                # Delete the file
                result = await self._delete_file(file_key)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("File deletion failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"File deletion failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def list_files(arguments: Dict[str, Any]) -> CallToolResult:
            """
            List files in S3 storage
            
            Args:
                prefix: Prefix to filter files (optional)
                max_keys: Maximum number of files to return (default: 100)
            """
            try:
                prefix = arguments.get("prefix", "")
                max_keys = arguments.get("max_keys", 100)
                
                # List files
                result = await self._list_files(prefix, max_keys)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("File listing failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"File listing failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def generate_presigned_url(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Generate a presigned URL for file access
            
            Args:
                file_key: S3 key of the file
                operation: Operation type ("get" or "put")
                expiration: URL expiration time in seconds (default: 3600)
            """
            try:
                file_key = arguments.get("file_key")
                operation = arguments.get("operation", "get")
                expiration = arguments.get("expiration", 3600)
                
                if not file_key:
                    raise ValueError("file_key is required")
                
                # Generate presigned URL
                result = await self._generate_presigned_url(file_key, operation, expiration)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("Presigned URL generation failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Presigned URL generation failed: {str(e)}"})
                    )],
                    isError=True
                )
    
    async def _upload_file(
        self,
        file_name: str,
        file_content: str,
        content_type: str,
        folder: str,
        public: bool
    ) -> Dict[str, Any]:
        """Upload file to S3"""
        
        if not self.s3_client or not self.s3_bucket:
            # Mock upload for development
            file_key = f"{folder}/{file_name}" if folder else file_name
            return {
                "file_key": file_key,
                "url": f"https://mock-bucket.s3.amazonaws.com/{file_key}",
                "size": len(base64.b64decode(file_content)),
                "content_type": content_type,
                "uploaded_at": datetime.now().isoformat(),
                "public": public,
                "note": "Mock upload - no AWS credentials configured"
            }
        
        try:
            # Decode base64 content
            file_data = base64.b64decode(file_content)
            
            # Create S3 key
            file_key = f"{folder}/{file_name}" if folder else file_name
            
            # Prepare upload parameters
            upload_params = {
                'Bucket': self.s3_bucket,
                'Key': file_key,
                'Body': file_data,
                'ContentType': content_type
            }
            
            # Set ACL if public
            if public:
                upload_params['ACL'] = 'public-read'
            
            # Upload to S3
            self.s3_client.put_object(**upload_params)
            
            # Generate URL
            if public:
                url = f"https://{self.s3_bucket}.s3.{self.aws_region}.amazonaws.com/{file_key}"
            else:
                url = await self._generate_presigned_url(file_key, "get", 3600)
                url = url["url"]
            
            return {
                "file_key": file_key,
                "url": url,
                "size": len(file_data),
                "content_type": content_type,
                "uploaded_at": datetime.now().isoformat(),
                "public": public
            }
            
        except Exception as e:
            logger.error("S3 upload failed", error=str(e))
            raise
    
    async def _download_file(self, file_key: str, return_content: bool) -> Dict[str, Any]:
        """Download file from S3"""
        
        if not self.s3_client or not self.s3_bucket:
            # Mock download for development
            return {
                "file_key": file_key,
                "content": base64.b64encode(b"Mock file content").decode() if return_content else None,
                "url": f"https://mock-bucket.s3.amazonaws.com/{file_key}" if not return_content else None,
                "size": 17,
                "content_type": "text/plain",
                "last_modified": datetime.now().isoformat(),
                "note": "Mock download - no AWS credentials configured"
            }
        
        try:
            if return_content:
                # Download file content
                response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=file_key)
                file_content = response['Body'].read()
                
                return {
                    "file_key": file_key,
                    "content": base64.b64encode(file_content).decode(),
                    "size": response['ContentLength'],
                    "content_type": response['ContentType'],
                    "last_modified": response['LastModified'].isoformat()
                }
            else:
                # Generate presigned URL
                url_result = await self._generate_presigned_url(file_key, "get", 3600)
                
                # Get file metadata
                response = self.s3_client.head_object(Bucket=self.s3_bucket, Key=file_key)
                
                return {
                    "file_key": file_key,
                    "url": url_result["url"],
                    "size": response['ContentLength'],
                    "content_type": response['ContentType'],
                    "last_modified": response['LastModified'].isoformat()
                }
                
        except Exception as e:
            logger.error("S3 download failed", error=str(e))
            raise
    
    async def _delete_file(self, file_key: str) -> Dict[str, Any]:
        """Delete file from S3"""
        
        if not self.s3_client or not self.s3_bucket:
            # Mock deletion for development
            return {
                "file_key": file_key,
                "deleted": True,
                "deleted_at": datetime.now().isoformat(),
                "note": "Mock deletion - no AWS credentials configured"
            }
        
        try:
            # Delete from S3
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=file_key)
            
            return {
                "file_key": file_key,
                "deleted": True,
                "deleted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("S3 deletion failed", error=str(e))
            raise
    
    async def _list_files(self, prefix: str, max_keys: int) -> Dict[str, Any]:
        """List files in S3"""
        
        if not self.s3_client or not self.s3_bucket:
            # Mock listing for development
            mock_files = []
            for i in range(min(max_keys, 3)):
                mock_files.append({
                    "key": f"{prefix}mock_file_{i+1}.txt",
                    "size": 100 + i * 50,
                    "last_modified": (datetime.now() - timedelta(days=i)).isoformat(),
                    "etag": f"mock_etag_{i+1}"
                })
            
            return {
                "files": mock_files,
                "total_count": len(mock_files),
                "prefix": prefix,
                "note": "Mock listing - no AWS credentials configured"
            }
        
        try:
            # List objects in S3
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "etag": obj['ETag'].strip('"')
                })
            
            return {
                "files": files,
                "total_count": len(files),
                "prefix": prefix,
                "is_truncated": response.get('IsTruncated', False)
            }
            
        except Exception as e:
            logger.error("S3 listing failed", error=str(e))
            raise
    
    async def _generate_presigned_url(
        self,
        file_key: str,
        operation: str,
        expiration: int
    ) -> Dict[str, Any]:
        """Generate presigned URL for S3 operations"""
        
        if not self.s3_client or not self.s3_bucket:
            # Mock presigned URL for development
            return {
                "url": f"https://mock-bucket.s3.amazonaws.com/{file_key}?presigned=true",
                "expiration": expiration,
                "expires_at": (datetime.now() + timedelta(seconds=expiration)).isoformat(),
                "operation": operation,
                "note": "Mock presigned URL - no AWS credentials configured"
            }
        
        try:
            # Map operation to S3 method
            method_map = {
                "get": "get_object",
                "put": "put_object"
            }
            
            if operation not in method_map:
                raise ValueError(f"Unsupported operation: {operation}")
            
            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                method_map[operation],
                Params={'Bucket': self.s3_bucket, 'Key': file_key},
                ExpiresIn=expiration
            )
            
            return {
                "url": url,
                "expiration": expiration,
                "expires_at": (datetime.now() + timedelta(seconds=expiration)).isoformat(),
                "operation": operation
            }
            
        except Exception as e:
            logger.error("Presigned URL generation failed", error=str(e))
            raise
    
    def get_server(self) -> Server:
        """Get the MCP server instance"""
        return self.server


# Create global MCP server instance
file_storage_mcp = FileStorageMCP()