from flask import Blueprint, jsonify, request

import threading
from browser.chrome import  GetInfoProfile
from state.session import session_profiles
from tasks.profiles import Profiles

tasks_profiles = Profiles()
profiles = Blueprint('profiles', __name__)
@profiles.route('/', methods=['GET'])
def list():
    cleaned_profiles = {}
    for key, value in session_profiles.items():
        cleaned_profiles[key] = {
            k: v for k, v in value.items() if k not in ['thread', 'stop_event']
        }
    return jsonify({'data': cleaned_profiles})

@profiles.route('create', methods=['POST'])
def create():
    try:
        data = request.json
        # Khởi tạo đối tượng GetInfoProfile
        info = GetInfoProfile(data)
        # Lấy thông tin profile
        profile = info.get_info()
        return jsonify(profile)
    except Exception as e:
        print("Loi khi tao profile: ", e)
        return jsonify({
            'message': f'Lỗi, không thể tạo profile: {str(e)}'
        }), 400


@profiles.route('start/<string:id>', methods=['POST'])
def start(id):
    stop_event = threading.Event()
    thread = threading.Thread(target=tasks_profiles.start, args=(id,))
    thread.daemon = True
    thread.start()
    session_profiles[str(id)] = {
        'stop_event': stop_event,
        'thread': thread,
        'check': 2,
        'status': 'Đang khởi tạo trình duyệt'
    }

    return jsonify({
        'message': 'Đang khởi tạo trình duyệt',
    })

@profiles.route('stop/<string:id>', methods=['POST'])
def stop(id):
    if id not in session_profiles:
        return jsonify({
            'message': 'Profile không tồn tại',
        }), 404
    session_profiles[str(id)]['stop_event'].set()
    thread = threading.Thread(target=tasks_profiles.close, args=(id,))
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': 'Trình duyệt đang bị dừng',
    })    