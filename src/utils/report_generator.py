"""
Report Generator Module
HTML ve JSON formatında raporlar oluşturur
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict
from jinja2 import Template

from ..utils.logger import get_logger


class ReportGenerator:
    """Rapor oluşturma"""
    
    REPORT_DIR = Path('/var/log/mstr-helper/reports')
    
    def __init__(self):
        self.logger = get_logger()
        self._ensure_report_dir()
    
    def _ensure_report_dir(self):
        """Rapor dizini oluştur"""
        try:
            self.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            self.REPORT_DIR = Path('/tmp/mstr-helper/reports')
            self.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    def generate_json_report(self, data: Dict, filename: str = None) -> str:
        """JSON rapor oluştur"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"mstr_helper_report_{timestamp}.json"
        
        report_path = self.REPORT_DIR / filename
        
        try:
            with open(report_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            self.logger.info(f"JSON rapor oluşturuldu: {report_path}")
            return str(report_path)
        except Exception as e:
            self.logger.error(f"JSON rapor oluşturulamadı: {str(e)}")
            return ""
    
    def generate_html_report(self, data: Dict, filename: str = None) -> str:
        """HTML rapor oluştur"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"mstr_helper_report_{timestamp}.html"
        
        report_path = self.REPORT_DIR / filename
        
        try:
            html_content = self._create_html_template(data)
            
            with open(report_path, 'w') as f:
                f.write(html_content)
            
            self.logger.info(f"HTML rapor oluşturuldu: {report_path}")
            return str(report_path)
        except Exception as e:
            self.logger.error(f"HTML rapor oluşturulamadı: {str(e)}")
            return ""
    
    def _create_html_template(self, data: Dict) -> str:
        """HTML template oluştur"""
        template_str = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>MicroStrategy Installation Helper - Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        .success {
            color: #27ae60;
            font-weight: bold;
        }
        .failure {
            color: #e74c3c;
            font-weight: bold;
        }
        .warning {
            color: #f39c12;
            font-weight: bold;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #3498db;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .info-box {
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }
        .timestamp {
            color: #7f8c8d;
            font-size: 14px;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-pass {
            background-color: #27ae60;
            color: white;
        }
        .status-fail {
            background-color: #e74c3c;
            color: white;
        }
        .status-warning {
            background-color: #f39c12;
            color: white;
        }
        .status-skip {
            background-color: #95a5a6;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>MicroStrategy Installation Helper - Report</h1>
        <p class="timestamp">Generated: {{ timestamp }}</p>
        
        <div class="info-box">
            <strong>Deployment Role:</strong> {{ deployment_role }}<br>
            <strong>Hostname:</strong> {{ hostname }}<br>
        </div>
        
        {% if checks %}
        <h2>System Checks</h2>
        <table>
            <tr>
                <th>Check</th>
                <th>Status</th>
                <th>Details</th>
            </tr>
            {% for check_name, check_data in checks.items() %}
            <tr>
                <td>{{ check_name }}</td>
                <td>
                    {% if check_data.passed %}
                    <span class="status-badge status-pass">PASS</span>
                    {% else %}
                    <span class="status-badge status-fail">FAIL</span>
                    {% endif %}
                </td>
                <td>{{ check_data.summary }}</td>
            </tr>
            {% endfor %}
        </table>
        {% endif %}
        
        {% if configurations %}
        <h2>Configurations</h2>
        <table>
            <tr>
                <th>Configuration</th>
                <th>Status</th>
                <th>Details</th>
            </tr>
            {% for config_name, config_data in configurations.items() %}
            <tr>
                <td>{{ config_name }}</td>
                <td>
                    {% if config_data.success %}
                    <span class="status-badge status-pass">SUCCESS</span>
                    {% else %}
                    <span class="status-badge status-fail">FAILED</span>
                    {% endif %}
                </td>
                <td>{{ config_data.message }}</td>
            </tr>
            {% endfor %}
        </table>
        {% endif %}
        
        <div class="info-box" style="margin-top: 30px;">
            <strong>Next Steps:</strong><br>
            1. Review any failed checks or configurations<br>
            2. Run MicroStrategy installer<br>
            3. After installation: <code>sudo mstr-helper verify</code>
        </div>
    </div>
</body>
</html>
"""
        
        template = Template(template_str)
        
        # Prepare template data
        template_data = {
            'timestamp': data.get('timestamp', datetime.now().isoformat()),
            'deployment_role': data.get('deployment_role', 'Unknown'),
            'hostname': data.get('hostname', 'Unknown'),
            'checks': {},
            'configurations': {}
        }
        
        # Process checks
        if 'checks' in data:
            for check_name, check_data in data['checks'].items():
                template_data['checks'][check_name] = {
                    'passed': check_data.get('passed', False),
                    'summary': self._summarize_check(check_data)
                }
        
        # Process configurations
        if 'configurations' in data:
            for config_name, config_data in data['configurations'].items():
                template_data['configurations'][config_name] = {
                    'success': config_data.get('success', False),
                    'message': config_data.get('results', {}).get('message', 'N/A')
                }
        
        return template.render(**template_data)
    
    def _summarize_check(self, check_data: Dict) -> str:
        """Check sonucunu özetle"""
        results = check_data.get('results', {})
        
        if not results:
            return "No data"
        
        # Her check tipine göre özet
        if 'cpu' in results:
            cpu = results['cpu']
            return f"{cpu.get('physical_cores', 0)} cores"
        elif 'memory' in results:
            mem = results['memory']
            return f"{mem.get('total_gb', 0)} GB"
        elif 'disk' in results:
            return "Disk space OK"
        elif 'ports' in results:
            ports = results['ports']
            return f"{ports.get('all_available', 'N/A')}"
        else:
            return "Completed"


if __name__ == '__main__':
    # Test
    generator = ReportGenerator()
    test_data = {
        'timestamp': datetime.now().isoformat(),
        'deployment_role': 'Combined',
        'hostname': 'test-server',
        'checks': {
            'system': {'passed': True, 'results': {'cpu': {'physical_cores': 8}}},
            'network': {'passed': True, 'results': {}}
        },
        'configurations': {
            'firewall': {'success': True, 'results': {'message': 'Configured successfully'}}
        }
    }
    
    json_path = generator.generate_json_report(test_data)
    html_path = generator.generate_html_report(test_data)
    print(f"JSON: {json_path}")
    print(f"HTML: {html_path}")
