"""System information controller"""

import socket
import subprocess
import asyncio
import concurrent.futures
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from presentation.middleware.auth import get_current_user
from infrastructure.database.models.user import User


class ServerIP(BaseModel):
    """Server IP information"""
    type: str
    ip: str
    description: str


class ServerIPsResponse(BaseModel):
    """Response model for server IPs"""
    success: bool
    ips: List[ServerIP]


def create_system_router() -> APIRouter:
    """Create system information router"""

    router = APIRouter(prefix="/system", tags=["system"])

    def fetch_ip_from_service(service_info):
        """Fetch IP from a service"""
        service, description = service_info
        try:
            if service.startswith('ipv6'):
                result = subprocess.run(
                    ["curl", "-s", "--connect-timeout", "3", "-6", service],
                    capture_output=True, text=True, timeout=8
                )
            else:
                result = subprocess.run(
                    ["curl", "-s", "--connect-timeout", "3", service],
                    capture_output=True, text=True, timeout=8
                )
            
            if result.returncode == 0 and result.stdout.strip():
                ip = result.stdout.strip()
                
                # Handle JSON responses (like HTTPBin)
                if ip.startswith('{') and 'origin' in ip:
                    try:
                        import json
                        data = json.loads(ip)
                        ip = data.get('origin', ip)
                    except:
                        pass
                
                return {"ip": ip, "description": description, "service": service}
        except:
            pass
        return None

    @router.get("/server-ips", response_model=ServerIPsResponse)
    async def get_server_ips():
        """
        Get comprehensive server IP addresses for exchange API whitelist
        
        Fetches multiple IPs in parallel from various sources
        """
        try:
            ips = []
            
            # Multiple IP detection services
            ip_services = [
                ("ifconfig.me", "🌐 Primary Public IP - ADD TO BINANCE"),
                ("ipecho.net/plain", "🌐 Public IP (Alternative source)"),
                ("icanhazip.com", "🌐 Public IP (Backup source)"),
                ("ipv4.icanhazip.com", "🌐 IPv4 Public IP"),
                ("checkip.amazonaws.com", "☁️ AWS IP Detection Service"),
                ("ip.seeip.org", "🌐 Public IP (SeeIP service)"),
                ("ipapi.co/ip", "🌐 Public IP (IPApi service)"),
                ("httpbin.org/ip", "🌐 Public IP (HTTPBin service)"),
            ]
            
            # Fetch IPs in parallel using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                future_to_service = {
                    executor.submit(fetch_ip_from_service, service_info): service_info 
                    for service_info in ip_services
                }
                
                seen_ips = set()
                for future in concurrent.futures.as_completed(future_to_service, timeout=15):
                    try:
                        result = future.result()
                        if result and result["ip"] not in seen_ips:
                            seen_ips.add(result["ip"])
                            
                            # Determine type based on service
                            ip_type = "public"
                            if "aws" in result["service"]:
                                ip_type = "cloud"
                            
                            ips.append(ServerIP(
                                type=ip_type,
                                ip=result["ip"],
                                description=result["description"]
                            ))
                    except Exception as e:
                        continue
            
            # Get IPv6 addresses separately
            try:
                ipv6_services = [
                    "ipv6.icanhazip.com",
                    "v6.ident.me", 
                    "ipv6.whatismyipaddress.com/ip"
                ]
                
                for service in ipv6_services:
                    try:
                        result = subprocess.run(
                            ["curl", "-s", "--connect-timeout", "3", "-6", service],
                            capture_output=True, text=True, timeout=8
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            ipv6 = result.stdout.strip()
                            if ipv6 not in seen_ips:
                                seen_ips.add(ipv6)
                                ips.append(ServerIP(
                                    type="ipv6",
                                    ip=ipv6,
                                    description="🌐 IPv6 Public IP (optional for exchanges)"
                                ))
                                break
                    except:
                        continue
            except:
                pass
            
            # Local/Container IPs
            try:
                hostname = socket.gethostname()
                local_ips = socket.gethostbyname_ex(hostname)[2]
                
                for ip in local_ips:
                    if not ip.startswith('127.') and ip not in seen_ips:
                        seen_ips.add(ip)
                        ips.append(ServerIP(
                            type="container",
                            ip=ip,
                            description=f"🐳 Container/Local IP ({hostname})"
                        ))
            except:
                pass
            
            # Network interfaces
            try:
                result = subprocess.run(
                    ["hostname", "-I"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    interface_ips = result.stdout.strip().split()
                    for ip in interface_ips:
                        if not ip.startswith('127.') and ip not in seen_ips:
                            seen_ips.add(ip)
                            
                            # Classify IP
                            if ip.startswith(('10.', '192.168.', '172.')):
                                desc = "🔧 Private Network Interface"
                            else:
                                desc = "🔧 Network Interface IP"
                                
                            ips.append(ServerIP(
                                type="interface",
                                ip=ip,
                                description=desc
                            ))
            except:
                pass
            
            # Gateway/Router IP
            try:
                result = subprocess.run(
                    ["ip", "route", "show", "default"], 
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if 'default via' in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                gateway_ip = parts[2]
                                if gateway_ip not in seen_ips:
                                    seen_ips.add(gateway_ip)
                                    ips.append(ServerIP(
                                        type="gateway",
                                        ip=gateway_ip,
                                        description="🏠 Gateway/Router IP"
                                    ))
                                break
            except:
                pass
            
            # Add common cloud ranges if we detect cloud environment
            if ips:
                main_ip = ips[0].ip
                
                # Common cloud provider CIDR ranges
                cloud_ranges = {
                    # AWS ranges (major ones)
                    "3.": "3.0.0.0/8 (AWS US East)",
                    "13.": "13.0.0.0/8 (AWS US East)",  
                    "52.": "52.0.0.0/8 (AWS Global)",
                    "54.": "54.0.0.0/8 (AWS Global)",
                    # Google Cloud ranges
                    "34.": "34.0.0.0/8 (Google Cloud)",
                    "35.": "35.0.0.0/8 (Google Cloud)",
                    # Azure ranges
                    "20.": "20.0.0.0/8 (Azure Global)",
                    "40.": "40.0.0.0/8 (Azure Global)",
                }
                
                ip_start = main_ip.split('.')[0] + '.'
                if ip_start in cloud_ranges:
                    range_info = cloud_ranges[ip_start]
                    ips.append(ServerIP(
                        type="cloud_range",
                        ip=range_info.split(' ')[0],
                        description=f"☁️ {range_info} - Possible IP range"
                    ))
            
            # DNS resolution alternatives
            try:
                # Get external IP via DNS
                dns_result = subprocess.run(
                    ["dig", "+short", "myip.opendns.com", "@resolver1.opendns.com"],
                    capture_output=True, text=True, timeout=5
                )
                if dns_result.returncode == 0 and dns_result.stdout.strip():
                    dns_ip = dns_result.stdout.strip()
                    if dns_ip not in seen_ips and dns_ip.replace('.', '').isdigit():
                        seen_ips.add(dns_ip)
                        ips.append(ServerIP(
                            type="dns",
                            ip=dns_ip,
                            description="🔍 DNS-resolved Public IP (OpenDNS)"
                        ))
            except:
                pass
            
            # Sort IPs: Public first, then others
            ips.sort(key=lambda x: (
                0 if x.type == "public" else
                1 if x.type == "cloud" else  
                2 if x.type == "dns" else
                3 if x.type == "ipv6" else
                4 if x.type == "container" else 5
            ))
            
            # Ensure we have at least one IP
            if not ips:
                try:
                    fallback = subprocess.run(
                        ["curl", "-s", "--connect-timeout", "5", "ifconfig.me"],
                        capture_output=True, text=True, timeout=10
                    )
                    if fallback.returncode == 0:
                        ips.append(ServerIP(
                            type="fallback",
                            ip=fallback.stdout.strip(),
                            description="🌐 Fallback Public IP - ADD TO BINANCE"
                        ))
                except:
                    ips.append(ServerIP(
                        type="error",
                        ip="Unable to detect",
                        description="❌ Could not determine public IP"
                    ))
            
            return ServerIPsResponse(success=True, ips=ips)
            
        except Exception as e:
            print(f"Error in get_server_ips: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve server IPs: {str(e)}"
            )

    return router