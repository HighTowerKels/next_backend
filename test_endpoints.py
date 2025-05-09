import pytest
import requests
import json
import time
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.test_results = []
        self.session = requests.Session()  # Use session for connection pooling
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'APITester/1.0'
        })
        
    def test_endpoint(self, test_name: str, method: str, endpoint: str, 
                     data: Optional[Dict] = None, token: Optional[str] = None,
                     expected_status: int = None, files: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Test API endpoint with enhanced error handling and validation
        
        Args:
            test_name: Descriptive name for the test
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request payload
            token: Authorization token
            expected_status: Expected HTTP status code
            files: Files to upload (for multipart requests)
        
        Returns:
            Parsed JSON response or None if request failed
        """
        test_result = {
            'name': test_name,
            'passed': False,
            'method': method,
            'endpoint': endpoint,
            'request_data': data,
            'response': None,
            'error': None,
            'status_code': None,
            'elapsed': None,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            start_time = time.time()
            
            # Determine if we're sending JSON or form data
            if files:
                response = self.session.request(
                    method,
                    url,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=15
                )
            else:
                response = self.session.request(
                    method,
                    url,
                    json=data,
                    headers=headers,
                    timeout=15
                )
                
            elapsed = time.time() - start_time
            
            test_result['status_code'] = response.status_code
            test_result['elapsed'] = elapsed
            test_result['response_headers'] = dict(response.headers)
            
            try:
                response_data = response.json() if response.content else None
                test_result['response'] = response_data
                
                # Determine if test passed
                status_ok = (expected_status and response.status_code == expected_status) or \
                           (not expected_status and response.status_code in [200, 201])
                
                if status_ok:
                    test_result['passed'] = True
                    print(f"✅ {test_name} - Success ({response.status_code}) [{elapsed:.2f}s]")
                else:
                    test_result['error'] = {
                        'message': f"Unexpected status code: {response.status_code}",
                        'expected': expected_status,
                        'details': response_data or response.text
                    }
                    print(f"❌ {test_name} - Failed (Status: {response.status_code}, Expected: {expected_status})")
                    print(f"Response: {response.text[:500]}")  # Print first 500 chars of response
                
                return response_data
                
            except json.JSONDecodeError:
                test_result['error'] = {
                    'message': "Invalid JSON response",
                    'raw_response': response.text
                }
                print(f"❌ {test_name} - Failed (Invalid JSON)")
                print(f"Raw Response: {response.text[:500]}")
                return None
                
        except requests.exceptions.RequestException as e:
            test_result['error'] = {
                'message': f"Request failed: {str(e)}",
                'type': type(e).__name__
            }
            print(f"❌ {test_name} - Failed (Request error: {str(e)})")
            return None
            
        finally:
            self.test_results.append(test_result)
    
    def generate_report(self, file_path: Optional[str] = None):
        """Generate detailed test report"""
        try:
            passed = sum(1 for test in self.test_results if test['passed'])
            failed = len(self.test_results) - passed
            success_rate = (passed / len(self.test_results)) * 100 if self.test_results else 0
            
            report = {
                'summary': {
                    'total_tests': len(self.test_results),
                    'passed': passed,
                    'failed': failed,
                    'success_rate': f"{success_rate:.1f}%",
                    'start_time': self.test_results[0]['timestamp'] if self.test_results else None,
                    'end_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': sum(t.get('elapsed', 0) for t in self.test_results)
                },
                'details': self.test_results
            }
            
            # Print to console
            print("\n" + "="*50)
            print("TEST REPORT".center(50))
            print("="*50)
            print(f"\nTotal Tests: {len(self.test_results)}")
            print(f"Passed: {passed} ({success_rate:.1f}%)")
            print(f"Failed: {failed}")
            
            if failed > 0:
                print("\n" + "FAILURE DETAILS".center(50, '-'))
                for test in self.test_results:
                    if not test['passed']:
                        print(f"\n🔴 {test['name']}")
                        print(f"URL: {test['method']} {self.base_url}/{test['endpoint'].lstrip('/')}")
                        print(f"Status: {test['status_code']}")
                        print(f"Time: {test.get('elapsed', '?')}s")
                        
                        if test['request_data']:
                            print("\nRequest Data:")
                            print(json.dumps(test['request_data'], indent=2))
                        
                        error = test['error']
                        if isinstance(error, dict):
                            print(f"\nError: {error.get('message', 'Unknown error')}")
                            if 'details' in error and error['details']:
                                print("Details:", str(error['details'])[:500])
                        elif error:
                            print(f"\nError: {error}")
                        
                        if test['response']:
                            print("\nResponse:")
                            print(json.dumps(test['response'], indent=2))
            
            # Calculate average response time
            if self.test_results:
                avg_time = sum(t.get('elapsed', 0) for t in self.test_results) / len(self.test_results)
                print(f"\nAverage Response Time: {avg_time:.2f}s")
                print("="*50 + "\n")
            
            # Save to file if requested
            if file_path:
                with open(file_path, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"Report saved to {file_path}")
        
        except Exception as e:
            print(f"Error generating report: {str(e)}")

@pytest.fixture(scope="module")
def api_tester():
    """Fixture that provides an APITester instance"""
    base_url = os.getenv('API_BASE_URL', 'http://localhost:8000/api/v1')
    print(f"\nInitializing API tester for: {base_url}")
    return APITester(base_url)

@pytest.fixture(scope="module")
def test_user():
    """Fixture that provides test user data with unique values"""
    timestamp = int(time.time())
    return {
        "email": f"testuser_{timestamp}@example.com",
        "username": f"testuser_{timestamp}",
        "phone_number": f"234{timestamp%100000000:08d}",  # Ensures valid Nigerian phone number
        "password": "Testpass123!",
        "first_name": "Test",
        "last_name": f"User{timestamp%1000}"
    }

def test_user_registration(api_tester, test_user):
    """Test user registration endpoint"""
    # Try registration with optional API key if needed
    api_key = os.getenv('REGISTRATION_API_KEY')
    if api_key:
        test_user['api_key'] = api_key
    
    response = api_tester.test_endpoint(
        "User Registration", 
        "POST", 
        "auth/register/", 
        test_user,
        expected_status=201
    )
    
    assert response is not None, "Registration failed - no response"
    assert api_tester.test_results[-1]['status_code'] == 201, \
        f"Registration failed with status {api_tester.test_results[-1]['status_code']}"
    assert 'email' in response, "Response missing email field"
    assert response['email'] == test_user['email'], "Email in response doesn't match request"

@pytest.fixture(scope="module")
def auth_token(api_tester, test_user):
    """Fixture that provides authentication token"""
    # Ensure user is registered first
    test_user_registration(api_tester, test_user)
    
    login_data = {
        "email": test_user['email'],
        "password": test_user['password']
    }
    
    response = api_tester.test_endpoint(
        "User Login", 
        "POST", 
        "auth/login/", 
        login_data,
        expected_status=200
    )
    
    assert response is not None, "Login failed - no response"
    assert 'access' in response, "Login response missing access token"
    
    print(f"\nObtained auth token for {test_user['email']}")
    return response['access']

def test_wallet_operations(api_tester, auth_token):
    """Test wallet operations"""
    # Add retry logic for eventual consistency
    max_retries = 3
    wallet_response = None
    
    for attempt in range(max_retries):
        wallet_response = api_tester.test_endpoint(
            "Get Wallet", 
            "GET", 
            "wallet/", 
            token=auth_token,
            expected_status=200
        )
        
        if wallet_response and 'wallet_id' in wallet_response:
            break
            
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Wallet not ready, retrying in {wait_time}s...")
            time.sleep(wait_time)
    
    assert wallet_response is not None, "Wallet operations failed after retries"
    assert 'wallet_id' in wallet_response, "Response missing wallet_id"
    assert 'balance' in wallet_response, "Response missing balance"
    
    return wallet_response['wallet_id']

def test_deposit_webhook(api_tester, auth_token):
    """Test deposit webhook"""
    wallet_id = test_wallet_operations(api_tester, auth_token)
    
    webhook_data = {
        "reference": f"TEST-DEP-{int(time.time())}",
        "amount": "5000.00",
        "wallet_id": wallet_id,
        "timestamp": "2023-01-01T00:00:00Z",
        "signature": "test_signature"
    }
    
    # Add webhook secret if required
    webhook_secret = os.getenv('WEBHOOK_SECRET')
    if webhook_secret:
        webhook_data['secret'] = webhook_secret
    
    response = api_tester.test_endpoint(
        "Deposit Webhook", 
        "POST", 
        "wallet/deposit/webhook/", 
        webhook_data,
        expected_status=200
    )
    
    assert response is not None, "Deposit webhook failed"
    
    # Verify balance update
    time.sleep(1)  # Allow for processing
    updated_wallet = api_tester.test_endpoint(
        "Verify Deposit", 
        "GET", 
        "wallet/", 
        token=auth_token,
        expected_status=200
    )
    
    assert updated_wallet is not None, "Failed to verify deposit"
    assert float(updated_wallet.get('balance', 0)) == 5000.00, \
        f"Unexpected balance: {updated_wallet.get('balance')}"

def test_withdrawal(api_tester, auth_token):
    """Test withdrawal endpoint"""
    withdrawal_data = {
        "amount": "1000.00",
        "bank_code": "058",
        "account_number": "1234567890",
        "account_name": "Test User",
        "narration": "Test withdrawal"
    }
    
    response = api_tester.test_endpoint(
        "Withdrawal", 
        "POST", 
        "wallet/withdraw/", 
        withdrawal_data, 
        token=auth_token,
        expected_status=200
    )
    
    assert response is not None, "Withdrawal failed"
    assert 'transaction_id' in response, "Response missing transaction_id"

def test_transfer(api_tester, auth_token):
    """Test transfer endpoint"""
    transfer_data = {
        "amount": "500.00",
        "recipient_wallet_id": "NEXARECIPIENT123",
        "narration": "Test transfer"
    }
    
    response = api_tester.test_endpoint(
        "Transfer", 
        "POST", 
        "wallet/transfer/", 
        transfer_data, 
        token=auth_token,
        expected_status=200
    )
    
    assert response is not None, "Transfer failed"
    assert 'transaction_id' in response, "Response missing transaction_id"

def test_airtime_purchase(api_tester, auth_token):
    """Test airtime purchase endpoint"""
    airtime_data = {
        "phone": "2348123456789",
        "amount": "500.00",
        "network": "MTN"
    }
    
    response = api_tester.test_endpoint(
        "Airtime Purchase", 
        "POST", 
        "airtime/buy/", 
        airtime_data, 
        token=auth_token,
        expected_status=200
    )
    
    assert response is not None, "Airtime purchase failed"
    assert 'transaction_id' in response, "Response missing transaction_id"

def test_generate_report(api_tester):
    """Generate final test report"""
    api_tester.generate_report("test_report.json")

def test_user_login(api_tester, test_user):
    """Test user login endpoint with better error handling"""
    login_data = {
        "email": test_user['email'],
        "password": test_user['password']
    }
    
    response = api_tester.test_endpoint(
        "User Login", 
        "POST", 
        "auth/login/", 
        login_data,
        expected_status=200
    )
    
    if not response:
        print("Login failed - no response")
        return None
        
    if 'error' in response:
        print(f"Login error: {response['error']}")
        return None
        
    if 'access' not in response:
        print("Login response missing access token")
        return None
        
    return response['access']

def main():
    """Main function for standalone execution"""
    tester = APITester(os.getenv('API_BASE_URL', 'http://localhost:8000/api/v1'))
    
    try:
        # 1. Register
        timestamp = int(time.time())
        user_data = {
            "email": f"testuser_{timestamp}@example.com",
            "username": f"testuser_{timestamp}",
            "phone_number": f"234{timestamp%100000000:08d}",
            "password": "Testpass123!",
            "first_name": "Test",
            "last_name": f"User{timestamp%1000}"
        }
        
        # Add API key if needed
        api_key = os.getenv('REGISTRATION_API_KEY')
        if api_key:
            user_data['api_key'] = api_key
        
        reg_response = tester.test_endpoint(
            "User Registration", 
            "POST", 
            "auth/register/", 
            user_data,
            expected_status=201
        )
        
        if not reg_response:
            raise Exception("Registration failed")

        # 2. Login
        login_data = {
            "email": user_data['email'],
            "password": user_data['password']
        }
        
        login_response = tester.test_endpoint(
            "User Login", 
            "POST", 
            "auth/login/", 
            login_data,
            expected_status=200
        )
        
        if not login_response or 'access' not in login_response:
            raise Exception("Login failed")
        
        token = login_response['access']
        
        # 3. Wallet operations
        wallet_response = tester.test_endpoint(
            "Get Wallet", 
            "GET", 
            "wallet/", 
            token=token,
            expected_status=200
        )
        
        if not wallet_response or 'wallet_id' not in wallet_response:
            raise Exception("Wallet operations failed")
        
        wallet_id = wallet_response['wallet_id']
        
        # 4. Test deposit webhook
        webhook_data = {
            "reference": f"TEST-DEP-{timestamp}",
            "amount": "5000.00",
            "wallet_id": wallet_id,
            "timestamp": "2023-01-01T00:00:00Z",
            "signature": "test_signature"
        }
        
        webhook_secret = os.getenv('WEBHOOK_SECRET')
        if webhook_secret:
            webhook_data['secret'] = webhook_secret
        
        tester.test_endpoint(
            "Deposit Webhook", 
            "POST", 
            "wallet/deposit/webhook/", 
            webhook_data,
            expected_status=200
        )
        
        # 5. Verify balance after deposit
        time.sleep(1)
        updated_wallet = tester.test_endpoint(
            "Verify Deposit", 
            "GET", 
            "wallet/", 
            token=token,
            expected_status=200
        )
        
        if not updated_wallet:
            raise Exception("Failed to verify deposit")
        
        print(f"Current Balance: {updated_wallet.get('balance')}")
        
        # 6. Test withdrawal
        withdrawal_data = {
            "amount": "1000.00",
            "bank_code": "058",
            "account_number": "1234567890",
            "account_name": "Test User",
            "narration": "Test withdrawal"
        }
        
        tester.test_endpoint(
            "Withdrawal", 
            "POST", 
            "wallet/withdraw/", 
            withdrawal_data, 
            token=token,
            expected_status=200
        )
        
        # 7. Test transfer
        transfer_data = {
            "amount": "500.00",
            "recipient_wallet_id": "NEXARECIPIENT123",
            "narration": "Test transfer"
        }
        
        tester.test_endpoint(
            "Transfer", 
            "POST", 
            "wallet/transfer/", 
            transfer_data, 
            token=token,
            expected_status=200
        )
        
        # 8. Test airtime purchase
        airtime_data = {
            "phone": "2348123456789",
            "amount": "500.00",
            "network": "MTN"
        }
        
        tester.test_endpoint(
            "Airtime Purchase", 
            "POST", 
            "airtime/buy/", 
            airtime_data, 
            token=token,
            expected_status=200
        )
        
    except Exception as e:
        print(f"\n⚠️ Error during test execution: {str(e)}")
    finally:
        tester.generate_report("test_report.json")

if __name__ == '__main__':
    main()