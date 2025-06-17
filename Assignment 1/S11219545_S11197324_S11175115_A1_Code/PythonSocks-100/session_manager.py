import time
import uuid
from datetime import datetime
from CustomSocket import send_data, receive_data

class SessionManager:
    def __init__(self):
        self.active_sessions = {}
        self.session_lookup = {}  # Maps session_id to user_id
        self.socket_to_session = {}  # Maps socket to session_id

    def create_session(self, user_id, role, name, socket=None):
        """Create a new session with unique session ID"""
        session_id = str(uuid.uuid4())
        session = {
            'session_id': session_id,
            'user_id': user_id,
            'role': role,
            'name': name,
            'login_time': datetime.now(),
            'is_active': True,
            'socket': socket  # Store the socket reference
        }
        self.active_sessions[user_id] = session
        self.session_lookup[session_id] = user_id
        if socket:
            self.socket_to_session[socket] = session_id
        return session
    
    # Add this method to check if a user already has an active session
    def user_has_active_session(self, user_id):
        """Check if a user already has an active session."""
        for session in self.active_sessions.values():
            if session['user_id'] == user_id:
                return True
        return False

    def end_session(self, session_id):
        """End a session using session ID"""
        user_id = self.session_lookup.get(session_id)
        if user_id:
            session = self.active_sessions.get(user_id)
            if session:
                if session.get('socket'):
                    self.socket_to_session.pop(session['socket'], None)
                del self.active_sessions[user_id]
            del self.session_lookup[session_id]
            return True
        return False

    def get_session_by_socket(self, socket):
        """Get session by socket"""
        session_id = self.socket_to_session.get(socket)
        if session_id:
            return self.get_session_by_id(session_id)
        return None

    def update_socket(self, session_id, socket):
        """Update the socket for an existing session"""
        user_id = self.session_lookup.get(session_id)
        if user_id and user_id in self.active_sessions:
            # Remove old socket mapping if exists
            old_socket = self.active_sessions[user_id].get('socket')
            if old_socket and old_socket in self.socket_to_session:
                del self.socket_to_session[old_socket]

            # Update with new socket
            self.active_sessions[user_id]['socket'] = socket
            if socket:
                self.socket_to_session[socket] = session_id
            return True
        return False

    def get_session_by_id(self, session_id):
        """Get session information using session ID"""
        user_id = self.session_lookup.get(session_id)
        if user_id:
            return self.active_sessions.get(user_id)
        return None
    
    def get_session(self, user_id):
        """Get information about a user's session"""
        return self.active_sessions.get(user_id)
    
    def is_active(self, user_id):
        """Check if a user has an active session"""
        session = self.get_session(user_id)
        return session is not None and session['is_active']
    
    def get_all_active_sessions(self):
        """Get list of all active sessions"""
        return [session for session in self.active_sessions.values() 
                if session['is_active']]
    
    def send_and_get_response(self, command, *args):
        """Modified to include session ID with every command"""
        try:
            # Construct message with session ID as first parameter
            message = f"{self.session_id}|{command}"
            if args:
                message += "|" + "|".join(str(arg) for arg in args)
            
            send_data(self.sock, message)
            return receive_data(self.sock)
        except Exception as e:
            return f"ERROR: {str(e)}"