from flask import Flask, request, jsonify, render_template
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cloudflare_api import CloudflareAPI
from config import CLOUDFLARE_CONFIG

app = Flask(__name__, template_folder='templates', static_folder='static')

# 初始化API客户端
if "api_token" in CLOUDFLARE_CONFIG:
    cf = CloudflareAPI(api_token=CLOUDFLARE_CONFIG["api_token"])
else:
    cf = CloudflareAPI(
        email=CLOUDFLARE_CONFIG["email"],
        global_key=CLOUDFLARE_CONFIG["global_key"]
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/zones', methods=['GET'])
def get_zones():
    zones = cf.get_zones()
    return jsonify(zones)

@app.route('/api/zones/<domain>/id', methods=['GET'])
def get_zone_id(domain):
    zone_id = cf.get_zone_id(domain)
    return jsonify({"zone_id": zone_id})

@app.route('/api/zones/<zone_id>/dns_records', methods=['GET'])
def get_dns_records(zone_id):
    record_type = request.args.get('type')
    name = request.args.get('name')
    records = cf.get_dns_records(zone_id, record_type, name)
    return jsonify(records)

@app.route('/api/zones/<zone_id>/dns_records', methods=['POST'])
def create_dns_record(zone_id):
    data = request.json
    success = cf.create_dns_record(
        zone_id,
        data.get('type'),
        data.get('name'),
        data.get('content'),
        data.get('ttl', 1),
        data.get('proxied', False)
    )
    return jsonify({"success": success})

@app.route('/api/zones/<zone_id>/dns_records/<record_id>', methods=['PUT'])
def update_dns_record(zone_id, record_id):
    data = request.json
    success = cf.update_dns_record(
        zone_id,
        record_id,
        data.get('type'),
        data.get('name'),
        data.get('content'),
        data.get('ttl', 1),
        data.get('proxied', False)
    )
    return jsonify({"success": success})

@app.route('/api/zones/<zone_id>/dns_records/<record_id>', methods=['DELETE'])
def delete_dns_record(zone_id, record_id):
    success = cf.delete_dns_record(zone_id, record_id)
    return jsonify({"success": success})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
