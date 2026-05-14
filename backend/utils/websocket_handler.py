"""
WebSocket Handler for Live Proctoring Status
Provides real-time updates for face verification, device detection, and audio detection
"""
from flask import request
import json
from datetime import datetime

# Initialize SocketIO (will be initialized in app.py)
socketio = None

def init_socketio(app):
    """Initialize SocketIO with the Flask app"""
    global socketio
    try:
        from flask_socketio import SocketIO, emit, join_room, leave_room
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
        
        # Register event handlers after socketio is initialized
        @socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            print(f"[WebSocket] Client connected: {request.sid}")
            emit('connected', {'message': 'Connected to proctoring service'})

        @socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            print(f"[WebSocket] Client disconnected: {request.sid}")

        @socketio.on('join_session')
        def handle_join_session(data):
            """Handle client joining a session room"""
            session_id = data.get('session_id')
            if session_id:
                room = f'session_{session_id}'
                join_room(room)
                print(f"[WebSocket] Client {request.sid} joined session {session_id}")
                emit('joined', {'session_id': session_id, 'room': room})

        @socketio.on('leave_session')
        def handle_leave_session(data):
            """Handle client leaving a session room"""
            session_id = data.get('session_id')
            if session_id:
                room = f'session_{session_id}'
                leave_room(room)
                print(f"[WebSocket] Client {request.sid} left session {session_id}")
                emit('left', {'session_id': session_id})
        
        return socketio
    except ImportError:
        print("[WebSocket] flask-socketio not available. WebSocket features disabled.")
        socketio = None
        return None

def emit_proctoring_status(session_id, status_type, data):
    """
    Emit proctoring status update to WebSocket clients
    Args:
        session_id: Interview session ID
        status_type: 'face', 'device', 'audio', 'gaze'
        data: Status data dictionary
    """
    if socketio:
        socketio.emit('proctoring_status', {
            'session_id': session_id,
            'type': status_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'session_{session_id}')

def emit_warning(session_id, warning_type, message, count=None):
    """
    Emit warning to WebSocket clients
    Args:
        session_id: Interview session ID
        warning_type: 'face', 'device', 'audio', 'gaze'
        message: Warning message
        count: Warning count (optional)
    """
    if socketio:
        socketio.emit('proctoring_warning', {
            'session_id': session_id,
            'warning_type': warning_type,
            'message': message,
            'count': count,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'session_{session_id}')

def emit_interview_status(session_id, status, data=None):
    """
    Emit interview status update
    Args:
        session_id: Interview session ID
        status: 'started', 'question', 'answer', 'completed', 'terminated'
        data: Additional data
    """
    if socketio:
        socketio.emit('interview_status', {
            'session_id': session_id,
            'status': status,
            'data': data or {},
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'session_{session_id}')

# Event handlers are registered inside init_socketio() function

