import json
import socket
import threading
import bcrypt
import logging
from datetime import datetime
import time
from collections import defaultdict

from CustomSocket import (
    create_tcp_socket, bind_socket, listen_for_connections, 
    accept_connection, send_data, receive_data, close_socket,
    create_tcp_socket_with_options, configure_tcp_keepalive, set_tcp_nodelay, set_buffer_sizes,
    perform_tcp_handshake, set_non_blocking, 
    SOCK_STATUS_OK, SOCK_STATUS_TIMEOUT, SOCK_STATUS_CLOSED, SOCK_STATUS_ERROR
)

from db import *

from session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Server settings
HOST = '127.0.0.1'
PORT = 5090


class ChatRoomManager:
    """Manages chat rooms and associated user sockets."""
    
    def __init__(self):
        # Structure: {tutorial_id: {"users": {user_id: {"primary": socket, "chat": socket}}, "messages": [...]}}
        self.rooms = defaultdict(lambda: {"users": {}, "messages": []})
        self.room_lock = threading.RLock()
    
    def add_socket(self, tutorial_id, user_id, socket, is_chat_socket=False):
        """Add a socket to the chat room for a specific user."""
        with self.room_lock:
            if tutorial_id not in self.rooms:
                self.rooms[tutorial_id] = {"users": {}, "messages": []}
                
            if user_id not in self.rooms[tutorial_id]["users"]:
                self.rooms[tutorial_id]["users"][user_id] = {"primary": None, "chat": None}
            
            socket_type = "chat" if is_chat_socket else "primary"
            
            # Close existing socket before replacing
            existing_socket = self.rooms[tutorial_id]["users"][user_id][socket_type]
            if existing_socket:
                try:
                    existing_socket.close()
                except:
                    pass
            
            self.rooms[tutorial_id]["users"][user_id][socket_type] = socket
            logger.info(f"Added {socket_type} socket for user {user_id} in tutorial {tutorial_id}")
            return True
    
    def remove_dead_socket(self, tutorial_id, dead_socket):
        """Remove a disconnected socket from the room."""
        with self.room_lock:
            if tutorial_id in self.rooms:
                for user_id, sockets in self.rooms[tutorial_id]["users"].items():
                    if sockets["primary"] == dead_socket:
                        sockets["primary"] = None
                    if sockets["chat"] == dead_socket:
                        sockets["chat"] = None
    
    def get_primary_sockets(self, tutorial_id, exclude_user_id=None):
        """Get one primary socket per user."""
        with self.room_lock:
            sockets = []
            if tutorial_id not in self.rooms:
                return sockets
                
            for user_id, user_sockets in self.rooms[tutorial_id]["users"].items():
                if exclude_user_id and user_id == exclude_user_id:
                    continue
                if user_sockets["primary"]:
                    sockets.append(user_sockets["primary"])
            return sockets
    
    def get_all_sockets(self, tutorial_id, exclude_user_id=None):
        """Get all sockets in the room (both primary and chat)."""
        with self.room_lock:
            sockets = []
            if tutorial_id not in self.rooms:
                return sockets
                
            for user_id, user_sockets in self.rooms[tutorial_id]["users"].items():
                if exclude_user_id and user_id == exclude_user_id:
                    continue
                if user_sockets["primary"]:
                    sockets.append(user_sockets["primary"])
                if user_sockets["chat"]:
                    sockets.append(user_sockets["chat"])
            return sockets
    
    def get_chat_sockets(self, tutorial_id, exclude_user_id=None):
        """Get only chat sockets - for message broadcasting."""
        with self.room_lock:
            sockets = []
            if tutorial_id not in self.rooms:
                return sockets
                
            for user_id, user_sockets in self.rooms[tutorial_id]["users"].items():
                if exclude_user_id and user_id == exclude_user_id:
                    continue
                if user_sockets["chat"]:
                    sockets.append(user_sockets["chat"])
            return sockets
    
    def remove_user(self, tutorial_id, user_id):
        """Remove a user from the chat room."""
        with self.room_lock:
            if tutorial_id in self.rooms and user_id in self.rooms[tutorial_id]["users"]:
                del self.rooms[tutorial_id]["users"][user_id]
                return True
            return False
    
    def close_room(self, tutorial_id):
        """Close and remove a chat room."""
        with self.room_lock:
            if tutorial_id in self.rooms:
                # Close all sockets first
                for user_id, sockets in self.rooms[tutorial_id]["users"].items():
                    for socket_type in ["primary", "chat"]:
                        if sockets[socket_type]:
                            try:
                                sockets[socket_type].close()
                            except:
                                pass
                # Remove the room
                del self.rooms[tutorial_id]
                return True
            return False
    
    def is_active(self, tutorial_id):
        """Check if a chat room exists and has users."""
        with self.room_lock:
            return tutorial_id in self.rooms and len(self.rooms[tutorial_id]["users"]) > 0


class TutorialServer:
    """Main tutorial server implementation."""
    
    def __init__(self):
        """Initialize the server with necessary managers."""
        self.session_manager = SessionManager()
        self.chat_manager = ChatRoomManager()
        
    def start(self, host=HOST, port=PORT):
        """Start the server and listen for incoming connections."""
        # Create socket with optimized TCP options
        server_socket = create_tcp_socket_with_options(
            nodelay=True,       # Disable Nagle's algorithm for better responsiveness
            reuse_addr=True,    # Allow reusing the address if server restarts
            keepalive=True,     # Enable keepalive to detect lost connections
            recv_buffer=32768,  # 32KB receive buffer for better performance
            send_buffer=32768   # 32KB send buffer for better performance
        )
        
        if not server_socket:
            logger.error("Failed to create socket")
            return
        
        # Bind to address and port
        if not bind_socket(server_socket, host, port):
            logger.error(f"Failed to bind to {host}:{port}")
            close_socket(server_socket, cleanup=True)
            return
        
        # Listen for connections
        if not listen_for_connections(server_socket, backlog=100):
            logger.error("Failed to start listening")
            close_socket(server_socket, cleanup=True)
            return
        
        logger.info(f"Server listening on {host}:{port} with custom TCP options")
        
        try:
            while True:
                # Accept client connection
                client_data = accept_connection(server_socket)
                if not client_data:
                    logger.error("Failed to accept client connection")
                    continue
                    
                client_socket, client_addr = client_data
                
                # Configure client socket for optimal performance
                try:
                    set_tcp_nodelay(client_socket, True)
                    configure_tcp_keepalive(client_socket, idle_time=60, interval=10, count=3)
                    set_buffer_sizes(client_socket, 16384, 16384)
                except Exception as e:
                    logger.warning(f"Failed to set socket options: {e}")
                
                logger.info(f"Client connected from {client_addr}")
                
                # Start a new thread to handle this client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,)
                )
                client_thread.daemon = True
                client_thread.start()
        except KeyboardInterrupt:
            logger.info("Server shutting down")
        finally:
            close_socket(server_socket, cleanup=True)
            logger.info("Server stopped")

    def handle_client(self, client_socket):
        """Handle a new client connection and authenticate."""
        logger.info(f"New client connection")

        # Receive login credentials with timeout
        result = receive_data(client_socket, timeout=10)
        if result['status'] != SOCK_STATUS_OK:
            logger.error(f"Failed to receive login data: {result['error']}")
            close_socket(client_socket)
            return
            
        login_data = result['data']
        
        if login_data.startswith("SESSION_AUTH|"):
            self._handle_session_auth(client_socket, login_data)
        else:
            self._handle_credential_auth(client_socket, login_data)
    
    def _handle_session_auth(self, client_socket, login_data):
        """Handle session-based authentication."""
        session_id = login_data.split("|")[1]
        session = self.session_manager.get_session_by_id(session_id)
        
        if session:
            # Valid session, create a new socket entry linked to same user
            user_id = session['user_id']
            role = session['role']
            
            # Send success response
            send_data(client_socket, f"SUCCESS:Session authenticated")
            
            # Start appropriate handler based on role
            if role == "tutor":
                self.handle_tutor(client_socket, user_id, session_id)
            else:  # student
                self.handle_student(client_socket, user_id, session_id)
        else:
            # Invalid session ID
            send_data(client_socket, "FAIL:Invalid session")
            close_socket(client_socket)
    
    def _handle_credential_auth(self, client_socket, login_data):
        """Handle username/password authentication."""
        try:
            # Split the login data into user_id and password
            user_id, password = login_data.strip().split("|")
            logger.info(f"Login attempt for user: {user_id}")
        except ValueError:
            logger.error("Malformed login data received")
            send_data(client_socket, "FAIL:Malformed login data")
            close_socket(client_socket)
            return

        # Verify user exists in the database
        user = get_user(user_id)
        if not user:
            logger.warning(f"Login failed - User not found: {user_id}")
            send_data(client_socket, "FAIL:User not found")
            close_socket(client_socket)
            return

        # Verify password using bcrypt
        try:
            if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
                logger.warning(f"Login failed - Incorrect password for user: {user_id}")
                send_data(client_socket, "FAIL:Incorrect password")
                close_socket(client_socket)
                return
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            send_data(client_socket, "FAIL:Authentication error")
            close_socket(client_socket)
            return
        # Check if this user is already logged in
        if self.session_manager.user_has_active_session(user_id):
            logger.warning(f"Login rejected - User {user_id} already has an active session")
            send_data(client_socket, "FAIL:Already logged in")
            close_socket(client_socket)
            return

        # Create a new session for the authenticated user
        session = self.session_manager.create_session(user_id, user['role'], user['name'], client_socket)
        session_id = session['session_id']

         # Ensure profile_pic is not None
        profile_pic = user['profile_pic']
        logger.info(f"User {user_id} ({user['role']}) logged in successfully - Session ID: {session_id}")
        logger.info(f"Profile picture for user {user_id}: {profile_pic}")

        # Send success response with role, name and session ID
        #send_data(client_socket, f"SUCCESS:{user['role']}:{user['name']}:{session_id}:{user['profile_pic']}")
            # Send success response with role, name, session ID, and profile picture
        send_data(client_socket, f"SUCCESS|{user['role']}|{user['name']}|{session_id}|{profile_pic}")
        try:
            # Route users to their role-specific handlers
            if user['role'] == 'admin':
                self.handle_admin(client_socket, session_id)
            elif user['role'] == 'tutor':
                self.handle_tutor(client_socket, user_id, session_id)
            elif user['role'] == 'student':
                self.handle_student(client_socket, user_id, session_id)
        finally:
            # Clean up when client disconnects
            logger.info(f"Session ended for user {user_id} (Session ID: {session_id})")
            self.session_manager.end_session(session_id)
            close_socket(client_socket)

    def verify_session(self, client_socket, cmd_session_id, expected_session_id):
        """Verify that the session ID in a command matches the expected one."""
        session = self.session_manager.get_session_by_id(cmd_session_id)
        if not session or cmd_session_id != expected_session_id:
            logger.warning(f"Invalid session attempt: {cmd_session_id}")
            send_data(client_socket, "FAIL:Invalid session")
            return False
        return True

    def handle_admin(self, client_socket, session_id):
        """Handle admin commands and operations."""
        logger.info(f"Admin handler started for session {session_id}")
        
        while True:
            result = receive_data(client_socket)
            if result['status'] != SOCK_STATUS_OK:
                logger.error(f"Failed to receive admin command: {result['error']}")
                break
                
            data = result['data']
            if not data:
                break  # Client disconnected

            parts = data.strip().split("|")
            if len(parts) < 2:
                logger.error("Invalid message format")
                continue

            cmd_session_id = parts[0]
            command = parts[1]
            
            # Verify session is valid
            if not self.verify_session(client_socket, cmd_session_id, session_id):
                continue

            logger.info(f"Admin command received: {command}")
            
            try:
                if command == "CREATE_USER":
                    self._handle_create_user(client_socket, parts)
                elif command == "CREATE_TUTORIAL":
                    self._handle_create_tutorial(client_socket, parts)
                elif command == "ASSIGN":
                    self._handle_assign(client_socket, parts)
                else:
                    logger.warning(f"Unknown admin command: {command}")
                    send_data(client_socket, "FAIL:Unknown command")
            except Exception as e:
                logger.error(f"Error handling admin command {command}: {str(e)}")
                send_data(client_socket, f"FAIL:Internal error: {str(e)}")
        
        logger.info(f"Admin handler ended for session {session_id}")

    def _handle_create_user(self, client_socket, parts):
        """Handle CREATE_USER admin command."""
        if len(parts) != 6:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        new_id = parts[2]
        name = parts[3]
        passwd = parts[4]
        role = parts[5]

        logger.info(f"Creating new user: {new_id} ({role})")
        
        if get_user(new_id):
            send_data(client_socket, "FAIL:User ID already exists")
        else:
            create_user(new_id, name, passwd, role)
            send_data(client_socket, "USER_CREATED")
    
    def _handle_create_tutorial(self, client_socket, parts):
        """Handle CREATE_TUTORIAL admin command."""
        if len(parts) != 4:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        tut_id = parts[2]
        tut_name = parts[3]

        if get_tutorial(tut_id):
            send_data(client_socket, "FAIL:Tutorial ID already exists")
        else:
            create_tutorial(tut_id, tut_name)
            send_data(client_socket, "TUTORIAL_CREATED")
    
    def _handle_assign(self, client_socket, parts):
        """Handle ASSIGN admin command."""
        if len(parts) != 4:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        uid = parts[2]
        tid = parts[3]

        role = get_user_role(uid)
        if not role:
            send_data(client_socket, "FAIL:User not found")
            return
            
        if role == "tutor" and is_tutor_already_assigned(tid):
            send_data(client_socket, "FAIL:Tutor already assigned to this tutorial")
            return
            
        if assign_user_to_tutorial(uid, tid):
            send_data(client_socket, "ASSIGNED")
        else:
            send_data(client_socket, "FAIL:Database error")

    def handle_tutor(self, client_socket, tutor_id, session_id):
        """Handle tutor-specific commands."""
        while True:
            result = receive_data(client_socket)
            if result['status'] != SOCK_STATUS_OK:
                logger.error(f"Failed to receive tutor command: {result['error']}")
                break
                
            data = result['data']
            if not data:
                break  # Client disconnected

            parts = data.strip().split("|")
            if len(parts) < 2:
                logger.error("Invalid message format")
                continue

            cmd_session_id = parts[0]
            command = parts[1]
            
            # Verify session is valid
            if not self.verify_session(client_socket, cmd_session_id, session_id):
                continue

            logger.info(f"Tutor command received: {command}")
            
            try:
                if command in ["ASSIGNED_TUTORIALS", "POLL_TUTOR_TUTORIALS"]:
                    self._handle_tutor_tutorials(client_socket, tutor_id)
                elif command == "TUTORIAL_STUDENTS":
                    self._handle_tutorial_students(client_socket, parts)
                elif command == "START_CHAT":
                    self._handle_start_chat(client_socket, parts, tutor_id)
                elif command == "CHECK_CHAT":
                    self._handle_check_chat(client_socket, parts, tutor_id)
                elif command == "CHAT_AUTH":
                    self._handle_chat_auth(client_socket, parts, cmd_session_id)
                elif command == "CHAT_MESSAGE":
                    self._handle_chat_message(client_socket, session_id, parts)
                elif command == "LEAVE_CHAT":
                    self._handle_disconnect_message(client_socket, session_id, parts)
                elif command == "END_CHAT":
                    self._handle_end_chat(client_socket, parts)
                elif command == "JOIN_CHAT":  # Allow tutors to use JOIN_CHAT too
                    self._handle_tutor_join_chat(client_socket, parts, tutor_id, session_id)
                # Add to handle_tutor method's command handling section:
                elif command == "GET_ATTENDANCE":
                    self._handle_get_attendance(client_socket, parts)


                else:
                    logger.warning(f"Unknown tutor command: {command}")
                    send_data(client_socket, "FAIL:Unknown command")
            except Exception as e:
                logger.error(f"Error handling tutor command {command}: {str(e)}")
                send_data(client_socket, f"FAIL:Internal error: {str(e)}")
    
    def _handle_tutor_tutorials(self, client_socket, tutor_id):
        """Handle ASSIGNED_TUTORIALS tutor command."""
        tutorials = get_user_tutorials(tutor_id)
        response = "|".join([f"{t['id']}::{t['name']}" for t in tutorials]) or "NONE"
        send_data(client_socket, response)
    
    def _handle_tutorial_students(self, client_socket, parts):
        """Handle TUTORIAL_STUDENTS tutor command."""
        if len(parts) < 3:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        tutorial_id = parts[2]
        students = get_students_in_tutorial(tutorial_id)
        response = "|".join([f"{s['id']}::{s['name']}" for s in students]) or "NONE"
        send_data(client_socket, response)
    
    def _handle_start_chat(self, client_socket, parts, tutor_id):
        """Handle START_CHAT tutor command."""
        if len(parts) < 4:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        tutorial_id = parts[2]
        try:
            duration = int(parts[3])
        except ValueError:
            send_data(client_socket, "FAIL:Invalid duration format")
            return
            
            # Modified to get chat session ID
        chat_session_id = start_chat(tutorial_id, tutor_id, duration)
        if chat_session_id:
            # Add tutor's socket to chat room
            self.chat_manager.add_socket(tutorial_id, tutor_id, client_socket, is_chat_socket=False)
                # Initialize attendance records
            initialize_attendance_for_session(chat_session_id, tutorial_id)

            # Start a timer thread for this chat session
            timer_thread = threading.Thread(
                target=self._chat_session_timer,
                args=(tutorial_id, duration),
                daemon=True
            )
            timer_thread.start()

            # Send success with chat session ID
            send_data(client_socket, f"CHAT_STARTED:{chat_session_id}")
        else:
            send_data(client_socket, "FAIL:Chat session already active")

    def _handle_tutor_join_chat(self, client_socket, parts, tutor_id, session_id):
        """Handle JOIN_CHAT tutor command."""
        if len(parts) < 3:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        tutorial_id = parts[2]
        
        # Check if chat is active and was started by this tutor
        chat = get_active_chat(tutorial_id)
        if not chat:
            send_data(client_socket, "FAIL:No active chat for this tutorial")
            return
            
        if chat['tutor_id'] != tutor_id:
            send_data(client_socket, "FAIL:Not authorized for this chat")
            return
        
        # Add tutor's socket to chat room
        self.chat_manager.add_socket(tutorial_id, tutor_id, client_socket, is_chat_socket=False)
        
        # Send join confirmation with chat session ID
        send_data(client_socket, f"CHAT_JOINED:{tutor_id}:{chat['chat_session_id']}")
        
        # Notify other participants that the tutor has rejoined
        tutor = get_user(tutor_id)
        tutor_name = get_user(tutor_id)['name'] 


        if tutor:
            profile_pic_url = tutor.get('profile_pic', '')
            for socket in self.chat_manager.get_chat_sockets(tutorial_id, exclude_user_id=tutor_id):
                try:
                    # Include profile pic URL in join message
                    send_data(socket, f"USER_JOINED|{tutor_id}|{tutor_name}|{profile_pic_url}")
                except Exception as e:
                    logger.error(f"Error notifying user of join: {str(e)}")


    def _handle_chat_auth(self, client_socket, parts, session_id):
        """Handle CHAT_AUTH command."""
        if len(parts) < 3:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        tutorial_id = parts[2]
        
        # Verify session exists
        session = self.session_manager.get_session_by_id(session_id)
        if not session:
            send_data(client_socket, "FAIL:Invalid session")
            return
            
        # Update socket mapping to include this socket
        user_id = session['user_id']
        
            # Add this socket to the chat room AS A CHAT SOCKET
        active_chat = get_active_chat(tutorial_id)
        if active_chat:
                # Get start_time and end_time from active_chat
            start_time = float(active_chat.get('start_time', 0))
            end_time = float(active_chat.get('end_time', 0))
            
            # Calculate duration from end_time and start_time
            total_duration_seconds = end_time - start_time
            duration_minutes = int(total_duration_seconds / 60)
            
            # Log the retrieved values
            logger.info(f"Chat time values: start={start_time}, end={end_time}, calculated_duration={duration_minutes}min")

            # Calculate remaining seconds directly from end_time
            current_time = time.time()
            remaining_seconds = max(0, int(end_time - current_time))
            
            # Log the calculation
            logger.info(f"Time remaining calculation: end={end_time}, current={current_time}, remaining={remaining_seconds}s")

            
            self.chat_manager.add_socket(tutorial_id, user_id, client_socket, is_chat_socket=True)
            send_data(client_socket, f"CHAT_CONNECTED|{remaining_seconds}")
            logger.info(f"Chat socket registered for {user_id} in tutorial {tutorial_id}")
            set_non_blocking(client_socket, True)
        else:
            send_data(client_socket, "FAIL:Chat room not found")
                
            # Modify the PARTICIPANTS data format in _handle_chat_auth:
        participants = []
        with self.chat_manager.room_lock:
            if tutorial_id in self.chat_manager.rooms:
                # Add all users in the room (excluding the current user)
                for participant_id in self.chat_manager.rooms[tutorial_id]["users"]:
                    if participant_id == user_id:
                        continue  # Skip the current user
                    user = get_user(participant_id)
                    if user:
                        profile_pic_url = user.get('profile_pic', '')
                        participants.append(f"{participant_id}|{user['name']}|{profile_pic_url}")
        # Send participant list to the chat socket
        if participants:
            participants_msg = "PARTICIPANTS|" + "||".join(participants)
            try:
                send_data(client_socket, participants_msg, flush=True)
                logger.info(f"Sent participant list to {user_id}'s chat socket")
            except Exception as e:
                logger.error(f"Error sending participant list: {str(e)}")

    def _handle_check_chat(self, client_socket, parts, user_id):
        """Check if a chat is active for a tutorial and if this user can join it."""
        if len(parts) < 3:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        tutorial_id = parts[2]
        chat = get_active_chat(tutorial_id)
        
        # Get the user's role to determine if they're a tutor or student
        user_role = get_user_role(user_id)
        
        if not chat:
            # No active chat for this tutorial
            send_data(client_socket, "NO_ACTIVE_CHAT")
            return
            
        if user_role == "tutor":
            # Tutor-specific logic: check if they started the chat
            if chat['tutor_id'] == user_id:
                # This tutor started the chat and can rejoin
                send_data(client_socket, f"CHAT_ACTIVE:{chat['chat_session_id']}")
            else:
                # Chat exists but was started by another tutor
                send_data(client_socket, "FAIL:Chat exists but was started by another tutor")
        
        elif user_role == "student":
            # Student-specific logic: check if they are enrolled in this tutorial
            tutorials = get_user_tutorials(user_id)
            if any(t['id'] == tutorial_id for t in tutorials):
                # Student is enrolled and can join the chat
                send_data(client_socket, f"CHAT_ACTIVE:{chat['chat_session_id']}")
            else:
                # Student is not enrolled in this tutorial
                send_data(client_socket, "FAIL:Not enrolled in this tutorial")
        
        else:
            # Unknown role or admin (who shouldn't join chats)
            send_data(client_socket, "FAIL:Invalid role for chat participation")

    def _handle_chat_message(self, client_socket, session_id, parts):
        """Handle CHAT_MESSAGE command."""
        if len(parts) < 4:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        tutorial_id = parts[2]
        message = parts[3]
        self._broadcast_chat_message(client_socket, session_id, tutorial_id, message)
    
    def _handle_end_chat(self, client_socket, parts):
        """Handle END_CHAT tutor command."""
        if len(parts) < 3:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        tutorial_id = parts[2]
        end_chat(tutorial_id)

        # Send notification to all sockets before closing
        for socket in self.chat_manager.get_chat_sockets(tutorial_id):
            try:
                send_data(socket, "CHAT_ENDED",flush=True)
            except:
                pass

        # Close and remove the chat room
        self.chat_manager.close_room(tutorial_id)

    def handle_student(self, client_socket, student_id, session_id):
        """Handle student-specific commands."""
        while True:
            result = receive_data(client_socket)
            if result['status'] != SOCK_STATUS_OK:
                logger.error(f"Failed to receive student command: {result['error']}")
                break
                
            data = result['data']
            if not data:
                break  # Client disconnected

            parts = data.strip().split("|")
            if len(parts) < 2:
                logger.error("Invalid message format")
                continue

            cmd_session_id = parts[0]
            command = parts[1]
            
            # Verify session is valid
            if not self.verify_session(client_socket, cmd_session_id, session_id):
                continue

            logger.info(f"Student command received: {command}")
            
            try:
                if command == "ASSIGNED_TUTORIALS":
                    self._handle_student_tutorials(client_socket, student_id)
                elif command == "TUTORIAL_STUDENTS":
                    self._handle_student_tutorial_students(client_socket, parts, student_id)
                elif command == "CHECK_CHAT":
                    self._handle_check_chat(client_socket, parts, student_id)
                elif command == "JOIN_CHAT":
                    self._handle_join_chat(client_socket, parts, student_id, session_id)
                elif command == "CHAT_AUTH":
                    self._handle_chat_auth(client_socket, parts, cmd_session_id)
                elif command == "CHAT_MESSAGE":
                    self._handle_chat_message(client_socket, session_id, parts)
                    
                elif command == "LEAVE_CHAT":
                    self._handle_disconnect_message(client_socket, session_id, parts)
                else:
                    logger.warning(f"Unknown student command: {command}")
                    send_data(client_socket, "FAIL:Unknown command")
            except Exception as e:
                logger.error(f"Error handling student command {command}: {str(e)}")
                send_data(client_socket, f"FAIL:Internal error: {str(e)}")
    
    def _handle_student_tutorials(self, client_socket, student_id):
        """Handle ASSIGNED_TUTORIALS student command."""
        tutorials = get_user_tutorials(student_id)
        response = "|".join([f"{t['id']}::{t['name']}" for t in tutorials]) or "NONE"
        send_data(client_socket, response)
    
    def _handle_student_tutorial_students(self, client_socket, parts, student_id):
        """Handle TUTORIAL_STUDENTS student command."""
        if len(parts) < 3:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        tutorial_id = parts[2]
        
        # Verify student is enrolled in this tutorial
        tutorials = get_user_tutorials(student_id)
        if not any(t['id'] == tutorial_id for t in tutorials):
            send_data(client_socket, "FAIL:Not authorized for this tutorial")
            return
            
        students = get_students_in_tutorial(tutorial_id)
        response = "|".join([f"{s['id']}::{s['name']}" for s in students]) or "NONE"
        send_data(client_socket, response)

    # Add this new method:
    def _handle_get_attendance(self, client_socket, parts):
        """Handle GET_ATTENDANCE tutor command."""
        if len(parts) < 4:
            send_data(client_socket, "FAIL:Invalid command format")
            return

        # Extract session ID and chat session ID from the command
        cmd_session_id = parts[0]
        chat_session_id = parts[2]

        # Verify the session ID
        session = self.session_manager.get_session_by_socket(client_socket)
        if not session or session['session_id'] != cmd_session_id:
            logger.warning(f"Invalid session attempt: GET_ATTENDANCE")
            send_data(client_socket, "FAIL:Invalid session")
            return

        # Fetch attendance data for the given chat session
        attendance_data = get_attendance_for_session(chat_session_id)

        # Convert to string format for transmission
        attendance_msg = "ATTENDANCE_UPDATE|" + json.dumps(attendance_data)

        # Send the attendance data to the tutor's chat socket
        user_id = session['user_id']
        tutorial_id = parts[3]  # Assuming tutorial_id is passed as the 4th part of the command
        user_sockets = self.chat_manager.rooms[tutorial_id]["users"].get(user_id, {})
        chat_socket = user_sockets.get("chat")

        if chat_socket:
            try:
                send_data(chat_socket, attendance_msg, timeout=0.2, flush=True)
                logger.info(f"Attendance data sent to tutor {user_id}'s chat socket")
            except Exception as e:
                logger.error(f"Error sending attendance to chat socket: {str(e)}")
                send_data(client_socket, "FAIL:Error sending attendance data")
        else:
            logger.warning(f"No chat socket found for tutor {user_id}")
            send_data(client_socket, "FAIL:No chat socket available")

    def _handle_join_chat(self, client_socket, parts, student_id, session_id):
        """Handle JOIN_CHAT student command."""
        if len(parts) < 3:
            send_data(client_socket, "FAIL:Invalid command format")
            return
            
        tutorial_id = parts[2]
        
        # Verify student is enrolled in this tutorial
        tutorials = get_user_tutorials(student_id)
        if not any(t['id'] == tutorial_id for t in tutorials):
            send_data(client_socket, "FAIL:Not authorized for this tutorial")
            return
            
        # Check if chat is active
        chat = get_active_chat(tutorial_id)
        if not chat:
            send_data(client_socket, "FAIL:No active chat for this tutorial")
            return
            
        # Update socket tracking
        if not self.session_manager.update_socket(session_id, client_socket):
            send_data(client_socket, "FAIL:Session update failed")
            return
         
        # Add to chat room with primary socket
        self.chat_manager.add_socket(tutorial_id, student_id, client_socket, is_chat_socket=False)

        student_name = get_user(student_id)['name'] 

        # Send join confirmation with tutor ID and chat session ID
        send_data(client_socket, f"CHAT_JOINED:{chat['tutor_id']}:{chat['chat_session_id']}")
    # Mark student as present with correct chat_session_id
        mark_student_present(chat['chat_session_id'], tutorial_id, student_id)

          
        # Broadcast attendance update to tutors
        self._broadcast_attendance_update(tutorial_id)

        # In _handle_join_chat method:
        # Notify others of the new participant
        student = get_user(student_id)


        if student:
            profile_pic_url = student.get('profile_pic', '')
            for socket in self.chat_manager.get_chat_sockets(tutorial_id, exclude_user_id=student_id):
                try:
                    # Include profile pic URL in join message
                    send_data(socket, f"USER_JOINED|{student_id}|{student_name}|{profile_pic_url}")
                except Exception as e:
                    logger.error(f"Error notifying user of join: {str(e)}")

    def _broadcast_chat_message(self, client_socket, session_id, tutorial_id, message):
        """Broadcast a chat message to all participants in a tutorial."""
        # Get the sender's session information
        session = self.session_manager.get_session_by_id(session_id)
        if not session:
            logger.warning(f"Chat message rejected - Invalid session: {session_id}")
            return False

        # Get the sender's name and ID
        sender_id = session['user_id']
        sender_name = session['name']

            # Get profile picture URL from database
        user = get_user(sender_id)
        profile_pic_url = user['profile_pic'] if user and 'profile_pic' in user else None

        
        
        # Ensure timestamp is properly formatted with colon
        timestamp = datetime.now().strftime("%H:%M")  # Format: HH:MM
        
        # Format the message
        formatted_message = f"MESSAGE|{sender_name}|{sender_id}|{timestamp}|{message}|{profile_pic_url}"
        
        # Send timeout to avoid blocking
        SEND_TIMEOUT = 0.2  # 200ms timeout
        # First try chat sockets - these are dedicated for messaging
        chat_sockets = self.chat_manager.get_chat_sockets(tutorial_id, exclude_user_id=sender_id)
        successful_sends = 0
        
        # Try chat sockets first
        if chat_sockets:
            for socket in chat_sockets:
                try:
                    result = send_data(socket, formatted_message, timeout=SEND_TIMEOUT, flush=True)
                    if result['status'] == SOCK_STATUS_OK:
                        successful_sends += 1
                    else:
                        # Remove dead socket
                        self.chat_manager.remove_dead_socket(tutorial_id, socket)
                except Exception as e:
                    logger.error(f"Error sending to chat socket: {str(e)}")
                    self.chat_manager.remove_dead_socket(tutorial_id, socket)
        
        # If no chat socket sends succeeded, fall back to primary sockets
        if successful_sends == 0:
            primary_sockets = self.chat_manager.get_primary_sockets(tutorial_id, exclude_user_id=sender_id)
            for socket in primary_sockets:
                try:
                    result = send_data(socket, formatted_message, timeout=SEND_TIMEOUT, flush=True)
                    if result['status'] == SOCK_STATUS_OK:
                        successful_sends += 1
                except Exception as e:
                    logger.error(f"Error sending to primary socket: {str(e)}")
        
        return successful_sends > 0
    
    def _handle_disconnect_message(self, client_socket, session_id, parts):
        """Handle student disconnection from chat."""
        if len(parts) < 3:
            logger.warning("Invalid LEAVE_CHAT format")
            return False
            
        # Get the tutorial ID from the message
        tutorial_id = parts[2]
        
        # Get the sender's session information
        session = self.session_manager.get_session_by_id(session_id)
        if not session:
            logger.warning(f"Leave chat message rejected - Invalid session: {session_id}")
            return False
        

        # Get the sender's ID
        sender_id = session['user_id']
        sender_name = session['name']
        #TODO modify to show name and id
        # Notify other participants that this user left
        for socket in self.chat_manager.get_chat_sockets(tutorial_id, exclude_user_id=sender_id):
            try:
                send_data(socket, f"USER_LEFT:{sender_id}:{sender_name}", flush=True)
            except Exception as e:
                logger.error(f"Error notifying about user leaving: {str(e)}")
                
            # Get active chat to retrieve chat_session_id
        chat = get_active_chat(tutorial_id)
        if chat:
            # Mark student as absent and update duration
            disconnect_attendance(chat['chat_session_id'], sender_id)
            
            # Broadcast attendance update to tutors
            self._broadcast_attendance_update(tutorial_id)
        
        self.chat_manager.remove_user(tutorial_id, sender_id)
        logger.info(f"User {sender_id} left chat room {tutorial_id}")
        
        return True
            
    def _chat_session_timer(self, tutorial_id, duration):
        """Timer thread for managing chat session duration."""
        logger.info(f"Starting chat timer for tutorial {tutorial_id} ({duration} minutes)")
        
        # Calculate when to send the 5-minute warning
        warning_time = duration - 5

        # Wait until it's time to send the warning
        if warning_time > 0:
            time.sleep(warning_time * 60)
            
            # Verify chat is still active before sending warning
            if get_active_chat(tutorial_id):
                for socket in self.chat_manager.get_chat_sockets(tutorial_id):
                    try:
                        send_data(socket, "WARNING:5 minutes remaining")
                    except:
                        pass

                # Wait for the remaining time (5 minutes after warning)
                time.sleep(5 * 60)
            else:
                logger.info(f"Chat for tutorial {tutorial_id} ended before warning")
                return
        else:
            # For short sessions (<5 min), just wait the full time
            time.sleep(duration * 60)

        # Verify chat is still active before ending
        if get_active_chat(tutorial_id):
            # End the chat session
            end_chat(tutorial_id)

            # Send end notification to all participants
            for socket in self.chat_manager.get_chat_sockets(tutorial_id):
                try:
                    send_data(socket, "CHAT_ENDED")
                except:
                    pass

            # Close the chat room
            self.chat_manager.close_room(tutorial_id)
            logger.info(f"Chat for tutorial {tutorial_id} ended by timer")
        else:
            logger.info(f"Chat for tutorial {tutorial_id} already ended")

    def _broadcast_attendance_update(self, tutorial_id):
        # Get active chat session for this tutorial
        active_chat = get_active_chat(tutorial_id)
        if not active_chat:
            return
            
        chat_session_id = active_chat.get('chat_session_id')
        if not chat_session_id:
            return
        
        # Get current attendance data
        attendance_data = get_attendance_for_session(chat_session_id)
        
        # Convert to string format for transmission
        attendance_msg = "ATTENDANCE_UPDATE|" + json.dumps(attendance_data)
        
        # Send to all tutor sockets in this room
        tutor_ids = []
        # First identify which users are tutors
        for user_id, user_sockets in self.chat_manager.rooms[tutorial_id]["users"].items():
            session = self.session_manager.get_session_by_socket(user_sockets.get("primary"))
            if session and session.get("role") == "tutor":
                tutor_ids.append(user_id)
        
        
        user_sockets = self.chat_manager.rooms[tutorial_id]["users"].get(user_id, {})
        chat_socket = user_sockets.get("chat")

        if chat_socket:
            try:
                send_data(chat_socket, attendance_msg, timeout=0.2, flush=True)
                logger.info(f"Attendance data sent to tutor {user_id}'s chat socket")
            except Exception as e:
                logger.error(f"Error sending attendance to chat socket: {str(e)}")
        else:
            logger.warning(f"No chat socket found for tutor {user_id}")

        
      
def main():
    """Initialize the server and start it."""
    setup_database()  # Initialize the database before starting the server
    server = TutorialServer()
    server.start()


if __name__ == "__main__":
    main()