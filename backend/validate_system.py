import requests, json, time
from datetime import datetime

print('Project Kavach - Comprehensive System Validation')
print('=' * 60)

base_url = 'http://localhost:8000'
test_results = []

def test_endpoint(name, method, endpoint, data=None, expected_status=200):
    try:
        url = f'{base_url}{endpoint}'
        if method == 'GET':
            response = requests.get(url, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=5)
        elif method == 'DELETE':
            response = requests.delete(url, timeout=5)
        success = response.status_code == expected_status
        test_results.append({
            'name': name,
            'method': method,
            'endpoint': endpoint,
            'status': response.status_code,
            'expected': expected_status,
            'success': success,
            'response_time': response.elapsed.total_seconds()
        })
        print(f'{name}: {response.status_code} ({response.elapsed.total_seconds():.3f}s)')
        return response.json() if response.headers.get('content-type', '').startswith('application/json') else None
    except Exception as e:
        test_results.append({
            'name': name,
            'method': method,
            'endpoint': endpoint,
            'status': 'ERROR',
            'expected': expected_status,
            'success': False,
            'error': str(e)
        })
        print(f' {name}: ERROR - {str(e)}')
        return None

print('\n Core API Health Check')
print('-' * 30)
test_endpoint('Health Check', 'GET', '/api/health')

print('\n Authentication Module')
print('-' * 30)
test_endpoint('Login', 'POST', '/api/auth/login', {'username': 'operator', 'password': 'op123'})

print('\n Threat Detection System')  
print('-' * 30)
test_endpoint('List Threats', 'GET', '/api/threats')
test_endpoint('Simulate Threat', 'POST', '/api/threats/seed', {'count': 2})
test_endpoint('Get Threats After Simulation', 'GET', '/api/threats')

print('\n Command & Control')
print('-' * 30)
test_endpoint('List Commands', 'GET', '/api/commands/log')
test_endpoint('Dispatch Command', 'POST', '/api/commands/dispatch', {'threat_id': '1', 'coordinates': {'lat': 28.5, 'lon': 77.6}})

print('\n Incident Management')
print('-' * 30)
test_endpoint('List Incidents', 'GET', '/api/incidents')
test_endpoint('Create Incident', 'POST', '/api/incidents', {'title': 'Test Incident - System Validation', 'description': 'Automated test incident for validation', 'severity': 'medium', 'threat_id': '1'})

print('\n Hash-Chain Ledger')
print('-' * 30)
test_endpoint('Get Ledger', 'GET', '/api/ledger')
test_endpoint('Verify Integrity', 'GET', '/api/ledger/verify')

print('\n Airspace Management')
print('-' * 30)
test_endpoint('Get Whitelist', 'GET', '/api/airspace/whitelist')
test_endpoint('Add to Whitelist', 'POST', '/api/airspace/whitelist', {'remote_id': 'TEST-DRONE-001'})

print('\n Operational Intelligence')
print('-' * 30)
test_endpoint('ROS Metrics', 'GET', '/api/ops/ros/summary')
test_endpoint('Risk Score', 'GET', '/api/ops/risk/score')

print('\n Summary Report')
print('=' * 60)
total_tests = len(test_results)
passed_tests = sum(1 for t in test_results if t['success'])
failure_rate = ((total_tests - passed_tests) / total_tests) * 100 if total_tests > 0 else 0
print(f'Total Tests: {total_tests}')
print(f'Passed: {passed_tests}')
print(f'Failed: {total_tests - passed_tests}')
print(f'Success Rate: {(passed_tests/total_tests)*100:.1f}%')
if failure_rate > 0:
    print(f'\n Failed Tests:')
    for test in test_results:
        if not test['success']:
            print(f'   {test["name"]}: {test.get("error", f"Expected {test["expected"]}, got {test["status"]}")}')
print(f'\n System Status: {"READY FOR DEMO" if failure_rate < 10 else "NEEDS ATTENTION"}')
