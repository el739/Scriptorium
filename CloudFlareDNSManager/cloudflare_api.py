import requests
import json
from typing import List, Dict, Optional

class CloudflareAPI:
    def __init__(self, api_token: str = None, email: str = None, global_key: str = None):
        """
        初始化Cloudflare API客户端
        
        参数:
        api_token: API Token (推荐)
        email: 邮箱地址 (使用Global API Key时需要)
        global_key: Global API Key
        """
        self.base_url = "https://api.cloudflare.com/client/v4"
        
        if api_token:
            self.headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }
        elif email and global_key:
            self.headers = {
                "X-Auth-Email": email,
                "X-Auth-Key": global_key,
                "Content-Type": "application/json"
            }
        else:
            raise ValueError("必须提供 api_token 或者 email+global_key")
    
    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """发送API请求"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            if hasattr(e.response, 'text'):
                print(f"错误详情: {e.response.text}")
            return None
    
    def get_zones(self) -> List[Dict]:
        """获取所有域名Zone"""
        result = self._make_request("GET", "/zones")
        if result and result.get("success"):
            return result.get("result", [])
        return []
    
    def get_zone_id(self, domain: str) -> Optional[str]:
        """根据域名获取Zone ID"""
        zones = self.get_zones()
        for zone in zones:
            if zone["name"] == domain:
                return zone["id"]
        return None
    
    def get_dns_records(self, zone_id: str, record_type: str = None, name: str = None) -> List[Dict]:
        """获取DNS记录"""
        endpoint = f"/zones/{zone_id}/dns_records"
        params = []
        
        if record_type:
            params.append(f"type={record_type}")
        if name:
            params.append(f"name={name}")
        
        if params:
            endpoint += "?" + "&".join(params)
        
        result = self._make_request("GET", endpoint)
        if result and result.get("success"):
            return result.get("result", [])
        return []
    
    def create_dns_record(self, zone_id: str, record_type: str, name: str, 
                         content: str, ttl: int = 1, proxied: bool = False) -> bool:
        """创建DNS记录"""
        data = {
            "type": record_type,
            "name": name,
            "content": content,
            "ttl": ttl,
            "proxied": proxied
        }
        
        result = self._make_request("POST", f"/zones/{zone_id}/dns_records", data)
        return result and result.get("success", False)
    
    def update_dns_record(self, zone_id: str, record_id: str, record_type: str, 
                         name: str, content: str, ttl: int = 1, proxied: bool = False) -> bool:
        """更新DNS记录"""
        data = {
            "type": record_type,
            "name": name,
            "content": content,
            "ttl": ttl,
            "proxied": proxied
        }
        
        result = self._make_request("PUT", f"/zones/{zone_id}/dns_records/{record_id}", data)
        return result and result.get("success", False)
    
    def delete_dns_record(self, zone_id: str, record_id: str) -> bool:
        """删除DNS记录"""
        result = self._make_request("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")
        return result and result.get("success", False)
    
    def list_dns_records(self, domain: str, record_type: str = None):
        """列出域名的DNS记录（用户友好的显示）"""
        zone_id = self.get_zone_id(domain)
        if not zone_id:
            print(f"未找到域名: {domain}")
            return
        
        records = self.get_dns_records(zone_id, record_type)
        if not records:
            print("未找到DNS记录")
            return
        
        print(f"\n{domain} 的DNS记录:")
        print("-" * 80)
        print(f"{'类型':<8} {'名称':<25} {'内容':<25} {'TTL':<8} {'代理':<6}")
        print("-" * 80)
        
        for record in records:
            proxied = "是" if record.get("proxied", False) else "否"
            print(f"{record['type']:<8} {record['name']:<25} {record['content']:<25} {record['ttl']:<8} {proxied:<6}")

def main():
    """示例使用方法"""
    # 使用API Token（推荐）
    api_token = "your-token-here"
    cf = CloudflareAPI(api_token=api_token)
    
    # 或使用Global API Key
    # email = "your_email@example.com"
    # global_key = "your_global_api_key_here"
    # cf = CloudflareAPI(email=email, global_key=global_key)
    
    domain = "yourdomain.com"  # 替换为你的域名
    
    # 列出所有域名
    print("你的所有域名:")
    zones = cf.get_zones()
    for zone in zones:
        print(f"- {zone['name']} (ID: {zone['id']})")
    
    # 获取Zone ID
    zone_id = cf.get_zone_id(domain)
    if not zone_id:
        print(f"未找到域名: {domain}")
        return
    
    # 列出DNS记录
    cf.list_dns_records(domain)
    
    # 示例：创建A记录
    # success = cf.create_dns_record(zone_id, "A", "test", "1.2.3.4", ttl=300)
    # if success:
    #     print("DNS记录创建成功")
    # else:
    #     print("DNS记录创建失败")

if __name__ == "__main__":
    main()