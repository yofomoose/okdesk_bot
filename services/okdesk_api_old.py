import aiohttp
import json
from typing import Optional, Dict, Any
import config

class OkdeskAPI:
    """Класс для работы с API Okdesk"""
    
    def __init__(self):
        self.base_url = config.OKDESK_API_URL
        self.token = config.OKDESK_API_TOKEN
        self.session = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        return aiohttp.ClientSession(
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Выполнить HTTP запрос к API Okdesk"""
        if not self.session:
            self.session = await self._get_session()
            
        # Формируем URL с API токеном в параметрах (как в примере)
        if '?' in endpoint:
            url = f"{self.base_url}{endpoint}&api_token={self.token}"
        else:
            url = f"{self.base_url}{endpoint}?api_token={self.token}"
        
        print(f"🔗 {method} {url}")
        
        try:
            request_kwargs = {}
            if data and method in ['POST', 'PUT', 'PATCH']:
                request_kwargs['json'] = data
            
            async with self.session.request(method, url, **request_kwargs) as response:
                response_text = await response.text()
                print(f"📊 Response status: {response.status}")
                print(f"📄 Response: {response_text[:200]}...")
                
                if response.status in [200, 201]:
                    try:
                        return await response.json()
                    except:
                        return {"success": True, "text": response_text}
                else:
                    print(f"❌ API Error {response.status}: {response_text}")
                    return None
                            
        except Exception as e:
            print(f"❌ Request error for {method} {endpoint}: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """Тестировать соединение с API Okdesk"""
        try:
            # Пробуем получить список компаний (простой запрос для проверки)
            response = await self._make_request("GET", "/companies", {"limit": 1})
            if response is not None:
                print("✅ Соединение с Okdesk API успешно!")
                return True
            else:
                print("❌ Не удалось подключиться к Okdesk API")
                return False
        except Exception as e:
            print(f"❌ Ошибка тестирования API: {e}")
            return False
    
    async def find_company_by_inn(self, inn: str) -> Optional[Dict]:
        """Найти компанию по ИНН"""
        endpoint = config.OKDESK_ENDPOINTS["companies"]
        params = {"search": inn}
        
        response = await self._make_request("GET", endpoint, params)
        if response and "companies" in response:
            for company in response["companies"]:
                # Ищем компанию с подходящим ИНН в различных полях
                if (company.get("inn") == inn or 
                    company.get("legal_inn") == inn or
                    inn in str(company.get("name", ""))):
                    return company
        return None
    
    async def create_issue(self, title: str, description: str, user_data: Dict) -> Optional[Dict]:
        """Создать заявку в Okdesk"""
        endpoint = config.OKDESK_ENDPOINTS["issues"]
        
        # Формируем данные для создания заявки
        issue_data = {
            "title": title,
            "description": description,
            "priority": "normal",
            "type": "task"
        }
        
        # Добавляем информацию о пользователе
        if user_data.get("user_type") == "physical":
            # Для физического лица
            issue_data["contact"] = {
                "name": user_data.get("full_name"),
                "phone": user_data.get("phone")
            }
        elif user_data.get("user_type") == "legal":
            # Для юридического лица
            if user_data.get("company_id"):
                issue_data["company_id"] = user_data["company_id"]
        
        response = await self._make_request("POST", endpoint, issue_data)
        return response
    
    async def get_issue(self, issue_id: int) -> Optional[Dict]:
        """Получить информацию о заявке"""
        endpoint = f"{config.OKDESK_ENDPOINTS['issues']}/{issue_id}"
        return await self._make_request("GET", endpoint)
    
    async def add_comment_to_issue(self, issue_id: int, content: str, is_public: bool = True) -> Optional[Dict]:
        """Добавить комментарий к заявке"""
        endpoint = config.OKDESK_ENDPOINTS["comments"].format(issue_id=issue_id)
        
        comment_data = {
            "content": content,
            "public": is_public
        }
        
        return await self._make_request("POST", endpoint, comment_data)
    
    async def get_issue_comments(self, issue_id: int) -> Optional[Dict]:
        """Получить комментарии к заявке"""
        endpoint = config.OKDESK_ENDPOINTS["comments"].format(issue_id=issue_id)
        return await self._make_request("GET", endpoint)
    
    async def create_equipment(self, equipment_data: Dict) -> Optional[Dict]:
        """Создать оборудование"""
        endpoint = config.OKDESK_ENDPOINTS["equipments"]
        return await self._make_request("POST", endpoint, equipment_data)
