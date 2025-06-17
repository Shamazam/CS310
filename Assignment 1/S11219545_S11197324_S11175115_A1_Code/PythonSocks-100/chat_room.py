from io import BytesIO
import json
import os
import time
import customtkinter as ctk  # Modern-looking UI toolkit (enhanced tkinter)
import tkinter as tk  # Standard tkinter for constants
from tkinter import scrolledtext, messagebox  # Additional UI components
from PIL import Image, ImageTk  # For handling images
import threading  # For running background tasks
from datetime import datetime

import requests  # For adding timestamps to messages
from CustomSocket import (
    create_tcp_socket, connect_to_server, send_data, receive_data, close_socket,
    SOCK_STATUS_OK, SOCK_STATUS_TIMEOUT, SOCK_STATUS_CLOSED, SOCK_STATUS_ERROR
)
# Server connection details
HOST = '127.0.0.1'  # Address of the server (same machine in this case)
PORT = 5090        # Port number (must match the server's port)

# ...existing code...

# Update color constants with new aesthetic from the image
COLORS = {
    "primary_bg": "#AEE9F9",      # Pastel blue
    "secondary_bg": "#FFD6F6",    # Pastel pink
    "system_msg_bg": "#FFF3C7",   # Light yellow
    "user_msg_bg": "#FFB6B9",     # Pastel pink
    "others_msg_bg": "#E0C3FC",   # Pastel purple
    "button_color": "#4CD6C9",    # Turquoise from image
    "border_color": "#8A2BE2",    # Purple
    "text_color": "#333333",      # Dark text
    "hover_color": "#8A7BF7",     # Slightly darker purple for hover
    
    # New colors from the image
    "hot_pink_bg": "#FF9DB0",     # Hot pink background
    "bright_yellow": "#FFDD4A",   # Bright yellow for buttons/accents
    "calculator_yellow": "#FFD700", # Calculator display yellow
    "lavender": "#C9A3FF",        # Lavender for secondary elements
    "folder_orange": "#FF9966",   # Folder orange
    "turquoise": "#4CD6C9",       # Turquoise for buttons
    "white": "#FFFFFF",           # White for text on dark backgrounds
    "online_text": "#0BDA51",     # pastel green for online/present students
    "offline_text": "#FA5053",    # pastel red for offline/absent students

}


# Add this near your COLORS dictionary
PROFILE_SIZE = (56, 56)  # Width, Height in pixels


class ChatRoom(ctk.CTk):
    """
    Chat room interface where students and tutors can exchange messages in real-time.
    
    This class creates a window with a chat display, a message entry field,
    and buttons for sending messages and ending the chat (for tutors).
    """
    def __init__(self, sock, user_id, user_name, tutorial_id, tutorial_name, session_id, is_tutor=False, tutor_id=None, chat_session_id = None,profile_pic_url = None,parent=None):
        """
        Initialize the chat room window with necessary data.
        """
        # Check if we're using a parent window or creating our own
        if parent:
            # Don't call super().__init__() - we're using the provided window
            self.window = parent
        else:
            # Initialize the parent class (CTk window)
            super().__init__()
            self.window = self  # Reference to self as the window

        # Store parameters as instance variables for later use
        self.sock = sock
        self.user_id = user_id
        self.user_name = user_name
        self.tutorial_id = tutorial_id
        self.tutorial_name = tutorial_name
        self.session_id = session_id
        self.is_tutor = is_tutor
        self.tutor_id = tutor_id  # Store the tutor_id
        self.chat_session_id = chat_session_id  # Store the chat session ID if provided
        self.profile_pic_url = profile_pic_url  # Store the profile picture URL if provided
        

        # Dictionary to track connected users
        self.connected_users = {}
        self.connected_users[user_id] = user_name

            # Add timer variables
        self.remaining_seconds = 0
        self.timer_running = False
        self.timer_update_interval = 1000  # Update every 1 second (1000ms)
    
        
        if not parent:
            self.title(f"Chat - {tutorial_name} ({user_name})")  # Set window title
            self.geometry("800x700")  # Increased width to accommodate the participants list

                # Set custom appearance
        ctk.set_appearance_mode("light")  # Use light mode as base
        ctk.set_default_color_theme("blue")

         # Cache for profile pictures
        self.profile_pictures = {}
        self.default_profile = None
        self.image_load_lock = threading.Lock()
            
        # Update main frame style
        self.main_frame = ctk.CTkFrame(self.window, fg_color=COLORS["primary_bg"])
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)

         
        
        # Create a frame for the chat area (left side)
        self.chat_frame = ctk.CTkFrame(self.main_frame, fg_color=COLORS["secondary_bg"], 
                                    corner_radius=15, border_width=2, 
                                    border_color=COLORS["border_color"])
        self.chat_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))

                #Create frame for the participants list (right side) with updated style
        self.participants_frame = ctk.CTkFrame(self.main_frame, width=250,  # Increased width from 150 to 250
                                            fg_color=COLORS["secondary_bg"], 
                                            corner_radius=15, border_width=2,
                                            border_color=COLORS["border_color"])
    
   # Create timer frame at the top
        self.timer_frame = ctk.CTkFrame(
            self.chat_frame,
            fg_color=COLORS["calculator_yellow"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"],
            height=40
        )
        self.timer_frame.pack(pady=(10, 5), padx=10, fill='x')

                # Create timer label
        self.timer_label = ctk.CTkLabel(
            self.timer_frame,
            text="⏱️ Time Remaining: --:--:--",
            font=("Arial", 16, "bold"),
            text_color=COLORS["text_color"]
        )
        self.timer_label.pack(pady=8)

        # Load default profile picture
        self.load_default_profile()

            # Pre-load your own profile picture if URL is provided
        if self.profile_pic_url:
            self.fetch_profile_picture(self.user_id, self.profile_pic_url)

        
          # Track sidebar visibility state
        self.sidebar_visible = False

                # Create the chat display area with custom styling
        self.chat_display = tk.Text(
            self.chat_frame, 
            wrap=ctk.WORD,
            bg=COLORS["secondary_bg"],
            fg=COLORS["text_color"],
            font=("Arial", 16),
            padx=10,
            pady=10,
            border=0,
            highlightthickness=0
        )
        self.chat_display.pack(pady=10, padx=10, fill='both', expand=True)
        self.chat_display.config(state='disabled')

            # Add custom scrollbar with ttk
        import tkinter.ttk as ttk
        style = ttk.Style()
        style.configure("Custom.Vertical.TScrollbar", 
                        background=COLORS["button_color"], 
                        troughcolor=COLORS["secondary_bg"], 
                        arrowcolor=COLORS["border_color"],
                        bordercolor=COLORS["border_color"])

        # Use ttk.Scrollbar instead of tk.Scrollbar
        chat_scrollbar = ttk.Scrollbar(self.chat_frame, style="Custom.Vertical.TScrollbar", command=self.chat_display.yview)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_display.config(yscrollcommand=chat_scrollbar.set)
      
        
        # Add a label for the participants section
        self.participants_label = ctk.CTkLabel(self.participants_frame, text="Participants", font=("Arial", 14, "bold"))
        self.participants_label.pack(pady=(10, 5), padx=5)

            
        # Style sidebar header
        self.sidebar_header = ctk.CTkFrame(self.participants_frame, fg_color=COLORS["turquoise"],
                                        corner_radius=12, border_width=2, 
                                        border_color=COLORS["border_color"])
        self.sidebar_header.pack(fill='x', pady=(10, 5), padx=5)


        # Style participants label
        self.participants_label = ctk.CTkLabel(
            self.sidebar_header, 
            text="✧ Participants ✧",
            font=("Arial", 18, "bold"),
            text_color=COLORS["white"]
        )
        self.participants_label.pack(side='left', padx=10, pady=5)


            
        # Style toggle button
        self.toggle_btn = ctk.CTkButton(
            self.sidebar_header,
            text="≪",
            command=self.toggle_sidebar,
            width=20,
            height=20,
            corner_radius=18,
            fg_color=COLORS["bright_yellow"],
            hover_color=COLORS["folder_orange"],
            text_color=COLORS["text_color"],
            border_width=2,
            border_color=COLORS["border_color"]
        )
        self.toggle_btn.pack(side='right', padx=5)

                
            # Replace listbox with scrollable frame for cards
        self.participants_scroll = ctk.CTkScrollableFrame(
            self.participants_frame,
            fg_color="transparent",
            corner_radius=0,
            border_width=0
        )
        self.participants_scroll.pack(pady=(5, 10), padx=10, fill='both', expand=True)

                # Dictionary to keep track of participant cards
        self.participant_cards = {}

        # Initialize sidebar as visible so the toggle function hides it
        self.sidebar_visible = True

        
                # Create a message input frame for the entry field and send button
        self.message_input_frame = ctk.CTkFrame(
            self.chat_frame,
            fg_color="transparent"
        )
        self.message_input_frame.pack(pady=5, padx=10, fill='x')

        # Create the message entry field with updated style
        self.msg_entry = ctk.CTkEntry(
            self.message_input_frame,
            placeholder_text="Type your message...",
            height=40,
            corner_radius=18,
            border_width=2,
            border_color=COLORS["border_color"],
            fg_color="white",
            text_color=COLORS["text_color"],
            font=("Arial", 16)
        )
        self.msg_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.msg_entry.bind("<Return>", self.send_message)

                
        # Create the send button with retro style
        self.send_btn = ctk.CTkButton(
            self.message_input_frame,
            text="Send ✧",
            font=("Arial", 16, "bold"),
            fg_color=COLORS["button_color"],
            hover_color=COLORS["hover_color"],
            text_color=COLORS["text_color"],
            corner_radius=18,
            border_width=2,
            border_color=COLORS["border_color"],
            height=40,
            width=100,  # Fixed width for better appearance
            command=self.send_message
        )
        self.send_btn.pack(side='right', padx=(0, 0))

        # Create a frame for action buttons to align them horizontally
        self.action_buttons_frame = ctk.CTkFrame(
            self.chat_frame,
            fg_color="transparent"
        )
        self.action_buttons_frame.pack(pady=5, padx=10, fill='x')


        # Style the disconnect button
        self.disconnect_btn = ctk.CTkButton(
            self.action_buttons_frame,
            text="Disconnect ✧",
            font=("Arial", 16, "bold"),
            fg_color="#FF6B6B",  # Red for attention
            hover_color="#FF4040",
            text_color="white",
            corner_radius=18,
            border_width=2,
            border_color=COLORS["border_color"],
            height=40,
            command=self.disconnect
        )
        self.disconnect_btn.pack(side='left', padx=5, expand=True, fill='x')


                # Add the end chat button if present (for tutors)
        if self.is_tutor:
            self.end_btn = ctk.CTkButton(
                self.action_buttons_frame,
                text="End Chat ✧",
                font=("Arial", 16, "bold"),
                fg_color="#FF6B6B",  # Red for attention
                hover_color="#FF4040",
                text_color="white",
                corner_radius=18,
                border_width=2,
                border_color=COLORS["border_color"],
                height=40,
                command=self.end_chat
            )
            self.end_btn.pack(side='left', padx=5, expand=True, fill='x')
              # Add the attendance button in the action button frame
            self.attendance_btn = ctk.CTkButton(
                self.action_buttons_frame,
                text="View Attendance ✧",
                font=("Arial", 16, "bold"),
                fg_color=COLORS["bright_yellow"],
                hover_color=COLORS["folder_orange"],
                text_color=COLORS["text_color"],
                corner_radius=18,
                border_width=2,
                border_color=COLORS["border_color"],
                height=40,
                command=self.show_attendance
            )
            self.attendance_btn.pack(side='left', padx=5, expand=True, fill='x')


        # Flag to control the message listener thread
        self.running = True
        
        self.create_chat_socket() # Create a chat socket for this window

        # Start a background thread to listen for incoming messages
        # daemon=True means this thread will exit when the main program exits
        self.listen_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        self.listen_thread.start()

        # Show a system message that the user has joined
        self.announce_join()
        self.toggle_sidebar()  # Start with sidebar hidden
        
        # Initialize participants list
        self.update_participants_list()
        # Connect window close button to our on_closing method
        
        # With:
        if parent:
            self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        else:
            self.protocol("WM_DELETE_WINDOW", self.on_closing)  

    def toggle_sidebar(self):
        """Toggle the visibility of the participants sidebar"""
        if self.sidebar_visible:
            # Hide the sidebar
            self.participants_frame.pack_forget()
            # Create a show button with Y2K styling
            self.show_btn = ctk.CTkButton(
                self.main_frame,
                text="✧ ≫ ✧",
                command=self.toggle_sidebar,
                width=40,
                height=120,
                corner_radius=15,
                fg_color=COLORS["bright_yellow"],
                hover_color=COLORS["folder_orange"],
                text_color=COLORS["text_color"],
                border_width=2,
                border_color=COLORS["border_color"],
                font=("Arial", 14, "bold")
            )
            self.show_btn.pack(side='right', fill='y', padx=(2, 0))
            self.sidebar_visible = False
        else:
            # Remove the show button if it exists
            if hasattr(self, 'show_btn'):
                self.show_btn.destroy()
            # Show the sidebar
            self.participants_frame.pack(side='right', fill='y', padx=(5, 0))
            self.sidebar_visible = True
        
        # Adjust the layout after toggling
        self.window.update_idletasks()

    def update_participants_list(self):
        """Update the participants list in the UI with styled cards"""
        
        # More thorough cleanup - destroy all widgets in the participants_scroll frame
        for widget in self.participants_scroll.winfo_children():
            widget.destroy()
            
        # Clear the dictionary
        self.participant_cards = {}
        
        # Add the tutor first (if present)
        if self.tutor_id in self.connected_users:
            self._add_participant_card(
                self.tutor_id,
                self.connected_users[self.tutor_id],
                is_tutor=True,
                is_self=self.tutor_id == self.user_id
            )
        
        # Add all other participants (excluding tutor)
        for user_id, user_name in self.connected_users.items():
            if user_id != self.tutor_id:
                self._add_participant_card(
                    user_id,
                    user_name,
                    is_tutor=False,
                    is_self=user_id == self.user_id
                )

    def update_participant_card(self, user_id):
            """Update a participant's card with their profile picture"""
            if user_id in self.participant_cards and user_id in self.profile_pictures:
                # Get the card
                card = self.participant_cards[user_id]
                
                # Remove the old card and create a new one with the profile picture
                if card:
                    card.destroy()
                
                # Re-add the participant card with updated profile
                user_name = self.connected_users.get(user_id, user_id)
                is_tutor = (user_id == self.tutor_id)
                is_self = (user_id == self.user_id)
                
                self._add_participant_card(user_id, user_name, is_tutor, is_self)

    def _add_participant_card(self, user_id, user_name, is_tutor=False, is_self=False):
        """Helper method to create a styled participant card"""
        
        # Choose colors based on type
        if is_self:
            bg_color = COLORS["user_msg_bg"]
            border_color = COLORS["border_color"]
            text_color = COLORS["text_color"]
        elif is_tutor:
            bg_color = COLORS["others_msg_bg"]
            border_color = COLORS["border_color"]
            text_color = COLORS["text_color"]
        else:
            bg_color = COLORS["primary_bg"]
            border_color = COLORS["border_color"]
            text_color = COLORS["text_color"]
        
        # Create card frame
        card = ctk.CTkFrame(
            self.participants_scroll,
            fg_color=bg_color,
            corner_radius=12,
            border_width=2,
            border_color=border_color
        )
        card.pack(fill='x', pady=5, padx=5)
        
        # Icon based on role
        icon = "👨‍🏫" if is_tutor else "👤"
        
        # Create content with icon
        content_frame = ctk.CTkFrame(
            card,
            fg_color=bg_color,
            corner_radius=10,
            border_width=0
        )
        content_frame.pack(fill='both', padx=8, pady=8)
        
        # Use profile picture if available
        profile_frame = None
        if hasattr(self, 'get_profile_image'):
            profile_img = self.get_profile_image(user_id)
            if profile_img:
                profile_frame = tk.Frame(
                    content_frame,
                    width=40,
                    height=40,
                    bg=bg_color
                )
                profile_frame.pack_propagate(False)
                profile_frame.pack(side='left', padx=(0, 8))
                
                img_label = tk.Label(
                    profile_frame,
                    image=profile_img,
                    bg=bg_color
                )
                img_label.pack(fill='both')
        
        # If no profile picture, use icon
        if not profile_frame:
            icon_label = ctk.CTkLabel(
                content_frame,
                text=icon,
                font=("Arial", 18),
                text_color=text_color
            )
            icon_label.pack(side='left', padx=(5, 10))
        
        # User info container
        info_frame = ctk.CTkFrame(
            content_frame,
            fg_color=bg_color,
            corner_radius=0,
            border_width=0
        )
        info_frame.pack(side='left', fill='both', expand=True)
        
        # Name label
        name_text = f"{user_name}"
        if is_tutor:
            name_text = f"Tutor: {user_name}"
        if is_self:
            name_text += " (You)"
            
        name_label = ctk.CTkLabel(
            info_frame,
            text=name_text,
            font=("Arial", 16, "bold"),
            text_color=text_color,
            anchor="w"
        )
        name_label.pack(fill='x', pady=(0, 2))
        
        # Status indicator (online by default)
        status_frame = ctk.CTkFrame(
            info_frame,
            fg_color=bg_color,
            corner_radius=0,
            border_width=0
        )
        status_frame.pack(fill='x')
        
        status_dot = ctk.CTkLabel(
            status_frame,
            text="●",
            font=("Arial", 14),
            text_color=COLORS["online_text"]
        )
        status_dot.pack(side='left')
        
        status_text = ctk.CTkLabel(
            status_frame,
            text="Online",
            font=("Arial", 12),
            text_color=COLORS["online_text"],
            anchor="w"
        )
        status_text.pack(side='left', padx=(2, 0))
        
        # Store the card reference
        self.participant_cards[user_id] = card

            # For the announce_join method:
    def announce_join(self):
        """Add a system message showing that the user has joined the chat."""
        timestamp = datetime.now().strftime("%H:%M")  # Get current time (HH:MM)
        self.display_message("System", f"{self.user_name}({self.user_id}) joined", timestamp)


    def disconnect(self):
        """Disconnect from the chat and return to panel"""
        if messagebox.askyesno("Disconnect", "Are you sure you want to disconnect?"):
            try:
                # First send the LEAVECHAT message
                leave_msg = f"{self.session_id}|LEAVE_CHAT|{self.tutorial_id}"
                send_data(self.sock, leave_msg, flush=True)
                
                # Give the message time to be sent
                time.sleep(0.2)
                
                self.redirect_to_dashboard()  # Redirect to dashboard
            


                self.running = False  # Stop the message listener
                close_socket(self.sock)  # Close the socket connection
                self.destroy()        # Close the window

                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to disconnect: {str(e)}")
                   
    def on_closing(self):
        """Handle window closing event."""
        try:
            # Send leave message before closing
            leave_msg = f"{self.session_id}|LEAVE_CHAT|{self.tutorial_id}"
            send_data(self.sock, leave_msg, flush=True)
            
            # Brief delay to allow message to be sent
            time.sleep(0.2)
            
            close_socket(self.sock)  # Close the socket connection
            self.running = False  # Stop the message listener

        except:
            pass

        self.destroy()  # Close the window

        
    def load_default_profile(self, image_path=None):
        try:
            if not image_path:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                image_path = os.path.join(script_dir, "system_icon.jpg")
                
                # If default doesn't exist, use built-in image
                if not os.path.exists(image_path):
                    # Create a simple colored square as default
                    img = Image.new('RGB', PROFILE_SIZE, color="#6495ED")
                    self.system_profile = ImageTk.PhotoImage(img)
                    self.default_profile = self.system_profile
                    
                    # Save it for future use
                    img.save(image_path)
                    return True
            
            img = Image.open(image_path)
            img = img.resize(PROFILE_SIZE, Image.Resampling.LANCZOS)
            self.system_profile = ImageTk.PhotoImage(img)
            self.default_profile = self.system_profile
            return True
        except Exception as e:
            print(f"Error loading profile: {e}")
            return False
        
    def fetch_profile_picture(self, user_id, profile_url):
        """Download and process a profile picture from URL"""
        try:
            response = requests.get(profile_url, timeout=3)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                # Always resize to the constant size
                img = img.resize(PROFILE_SIZE, Image.Resampling.LANCZOS)
                with self.image_load_lock:
                    self.profile_pictures[user_id] = ImageTk.PhotoImage(img)
                return True
        except Exception as e:
            print(f"Error loading profile picture: {e}")
        return False

    def get_profile_image(self, user_id):
        """Get profile image for a user or the default if not available"""
        with self.image_load_lock:
            if user_id in self.profile_pictures:
                return self.profile_pictures[user_id]
        return self.default_profile
    


    def display_message(self, sender, message, timestamp=None, profile_url=None):
        # Enable editing
        self.chat_display.config(state='normal')
        
        # Use provided timestamp or current time
        display_time = timestamp or datetime.now().strftime('%H:%M')

        
        
        # Determine message type and styling
        if sender == "System":
            msg_type = "system"
            user_id = "system"
            card_bg = COLORS["system_msg_bg"]
            align = 'center'
        elif sender == "You":
            msg_type = "self"
            user_id = self.user_id
            card_bg = COLORS["user_msg_bg"]
            align = 'right'
        else:
            msg_type = "other"
            card_bg = COLORS["others_msg_bg"]
            align = 'left'
            user_id = "other_user"
        
        
        # Extract user ID from sender format: "Name(ID)"
        import re
        match = re.search(r'\(([^)]+)\)', sender)
        user_id = match.group(1) if match else "other_user"
        
        # If we have a profile URL and it's not already loaded, fetch it
        if profile_url and user_id not in self.profile_pictures:
            self.fetch_profile_picture(user_id, profile_url)
        
        # Get the current position
        msg_pos = self.chat_display.index('end-1c')
        
        # Add space between messages
        if self.chat_display.index('end-1c') != '1.0':
            self.chat_display.insert('end', '\n\n')
        
            # Change this line: Create the message card frame with rounded corners
        message_frame = ctk.CTkFrame(
            self.chat_display, 
            fg_color=card_bg,
            corner_radius=15,  # Controls the roundness of corners
            border_width=2,
            border_color=COLORS["border_color"]
        )
    
            # Change this line: Create content frame with rounded corners
        content_frame = ctk.CTkFrame(
            message_frame, 
            fg_color=card_bg,
            corner_radius=12,  # Slightly smaller corner radius
            border_width=0     # No border for inner frame
        )
        content_frame.pack(padx=8, pady=8)
        
        # Add profile picture if available
        if profile_img := self.get_profile_image(user_id):
            if msg_type != "system":
                # Create a fixed-size frame to hold the profile picture
                pic_frame = tk.Frame(
                    content_frame,
                    width=56,
                    height=56,
                    bg=card_bg
                )
                pic_frame.pack_propagate(False)  # Prevent the frame from shrinking
                
                # Put the image in the fixed-size frame
                img_label = tk.Label(
                    pic_frame,
                    image=profile_img,
                    bg=card_bg
                )
                img_label.image = profile_img  # Keep reference
                img_label.pack(fill="both", expand=True)
                
                # Pack the frame on the appropriate side
                if msg_type == "self":
                    pic_frame.pack(side="right", padx=(8, 0))
                else:
                    pic_frame.pack(side="left", padx=(0, 8))
            
        # Text content container with rounded corners
        text_container = ctk.CTkFrame(
            content_frame,
            fg_color=card_bg, 
            corner_radius=10,   # Even smaller corner radius
            border_width=0      # No border
        )
            
        # Sender name
        sender_label = tk.Label(
            text_container,
            text=sender,
            font=("Arial", 18, "bold"),
            fg=COLORS["text_color"],
            bg=card_bg,
            anchor="w" if msg_type != "self" else "e",
            justify="left" if msg_type != "self" else "right"
        )
        sender_label.pack(fill="x")
        
        # Message content
        msg_label = tk.Label(
            text_container,
            text=message,
            font=("Arial", 20),
            fg=COLORS["text_color"],
            bg=card_bg,
            anchor="w" if msg_type != "self" else "e",
            justify="left",
            wraplength=400  # Control width here
        )
        msg_label.pack(fill="x", pady=(2, 4))
        
        # Timestamp
        time_label = tk.Label(
            text_container,
            text=display_time,
            font=("Arial", 16),
            fg="#36454F",
            bg=card_bg,
            anchor="e" if msg_type == "self" else "w"
        )
        time_label.pack(fill="x")
        
        # Pack text container on appropriate side
        if msg_type == "self":
            text_container.pack(side="right")
        else:
            text_container.pack(side="left")
        
        # Insert the message with appropriate alignment
        align_tag = f"align_{msg_pos}"
        self.chat_display.insert('end', '\n')
        
        # Create a line with the right alignment and insert the window
        if align == "right":
            self.chat_display.insert('end', '\t\t\t', align_tag)  # Right-align with tabs
            self.chat_display.tag_configure(align_tag, justify='right')
        elif align == "center":
            self.chat_display.insert('end', '\t\t', align_tag)    # Center with tabs
            self.chat_display.tag_configure(align_tag, justify='center')
        
        # Insert the frame at the current position
        self.chat_display.window_create('end', window=message_frame)
        
        # Disable editing
        self.chat_display.config(state='disabled')
        
        # Scroll to newest message
        self.chat_display.see('end')

    def send_message(self, event=None):
        """
        Send a message to the server.

        Parameters:
            event:z Optional event data (when triggered by Enter key)
        """
        # Get the message from the entry field
        message = self.msg_entry.get().strip()

        # Only send if there is a message
        if message:
            try:
                # Format the command string
                command = f"{self.session_id}|CHAT_MESSAGE|{self.tutorial_id}|{message}"
                
                # Send message to server
                result = send_data(self.sock, command, timeout=0.1, flush=True)
                
                # Small delay to ensure network processing
                time.sleep(0.05)

                # Process result
                if result['status'] == SOCK_STATUS_OK:
                    print("Message sent successfully")
                    # Display the message locally so sender can see it
                    current_time = datetime.now().strftime("%H:%M")
                    # Just display the message content without timestamp in the content
                    self.display_message("You", message, current_time, self.profile_pic_url)
                    # Clear the message entry field
                    self.msg_entry.delete(0, 'end')
                else:
                    error_message = "Network error" if result['status'] == SOCK_STATUS_ERROR else "Connection lost"
                    print(f"Send error: {result['status']} - {error_message}")
                    messagebox.showerror("Error", f"Failed to send message: {error_message}")
                    
            except Exception as e:
                print(f"Exception when sending message: {str(e)}")
                messagebox.showerror("Error", f"Failed to send message: {str(e)}")

    def listen_for_messages(self):
        """
        Background thread that continuously listens for incoming messages from the server.
        Messages can be chat messages, user join notifications, or chat end signals.
        """
        while self.running:
            try:
                # Wait for data from the server with timeout
                result = receive_data(self.chat_sock, buffer_size=8192, timeout=0.1)
                
                # Handle different result statuses
                if result['status'] == SOCK_STATUS_TIMEOUT:
                    # Just a timeout, continue waiting
                    continue
                    
                elif result['status'] != SOCK_STATUS_OK:
                    # Connection closed or error
                    if result['status'] == SOCK_STATUS_CLOSED:
                        self.display_message("System", "Connection closed by server")
                    else:
                        self.display_message("System", f"Connection error: {result['error']}")
                    break  # Exit the loop
                
                # Process the received data
                data = result['data']
                
               # In the listen_for_messages method, update the MESSAGE handling block:
                # Handle different message types
                if data.startswith("MESSAGE|"):
                    # Format: MESSAGE|sender_name|sender_id|timestamp|message|profile_url
                    parts = data.split("|", 5)
                    if len(parts) >= 5:
                        sender_name = parts[1]
                        sender_id = parts[2]
                        timestamp = parts[3]
                        message_text = parts[4]
                        profile_url = parts[5] if len(parts) > 5 else None
                        
                        # Determine how to display sender
                        if sender_id == self.user_id:
                            display_name = "You"
                        elif sender_id == self.tutor_id:
                            display_name = f"Tutor ({sender_name})"
                        else:
                            display_name = f"{sender_name}({sender_id})"
                        
                        # Show the message with profile
                        self.display_message(display_name, message_text, timestamp, profile_url)
                    else:
                        # Fallback for malformed messages
                        self.display_message("System", f"Received malformed message: {data}")
                
                    # Modify USER_JOINED handling to use pipe characters instead of colons
                elif data.startswith("USER_JOINED|"):
                    # New Format: USER_JOINED|user_id|user_name|profile_url
                    parts = data.split("|", 3)
                    user_id = parts[1]
                    
                    # Get user name from message if provided, otherwise use ID
                    user_name = parts[2] if len(parts) > 2 else user_id
                    profile_url = parts[3] if len(parts) > 3 else None
                    timestamp = datetime.now().strftime("%H:%M")

                    print('User joined:', user_id, user_name, profile_url)
                    
                    # If we have a profile URL, fetch it
                    if profile_url and user_id not in self.profile_pictures:
                        if self.fetch_profile_picture(user_id, profile_url):
                            # Update the participant card immediately after fetching the profile picture
                            self.update_participant_card(user_id)
                        
                    # Add to connected users with proper name - only if not already present
                    if user_id not in self.connected_users:
                        self.connected_users[user_id] = user_name
                        self.update_participants_list()

                        # Display the join notification
                    self.display_message("System", f"{user_name}({user_id}) joined the chat", timestamp)

                elif data.startswith("USER_LEFT:"):
                    parts = data.split(":", 2)
                    user_id = parts[1]
                    # Format: USER_LEFT:user_id
                    timestamp = datetime.now().strftime("%H:%M")
                    
                    # Get username before removing
                    user_name = self.connected_users.get(user_id, user_id)

                    
                    # Remove from connected users
                    if user_id in self.connected_users:
                        del self.connected_users[user_id]
                        self.update_participants_list()
                    
                    # Display the leave notification
                    self.display_message("System", f"{user_name}({user_id}) left the chat", timestamp)

                                # In listen_for_messages method, enhance the WARNING handling:
                elif data.startswith("WARNING:"):
                    # Display the time warning
                    warning_msg = data.split(":", 1)[1]
                    self.display_message("System", warning_msg)
                    
                    # Update timer display to indicate warning state
                    self.timer_label.configure(text_color=COLORS["offline_text"])
                    self.timer_frame.configure(fg_color="#FFEEEE")  # Light pink warning color

                elif data == "CHAT_ENDED":
                    # Handle chat ended message
                    self.display_message("System", "Chat session has ended")
                 # Close the chat window and redirect after a short delay
                    self.after(1000, self.redirect_to_dashboard)
                    self.running = False

                # To this:
                elif data.startswith("ATTENDANCE_UPDATE|"):                    # Handle attendance update
                    try:
                        _, attendance_json = data.split("|", 1)
                        attendance_data = json.loads(attendance_json)
                        
                        # Update attendance window if it exists
                        if hasattr(self, 'attendance_window') and self.attendance_window:
                            self.attendance_window.update_attendance(attendance_data)
                    except Exception as e:
                        print(f"Error handling attendance update: {e}")
                # Update PARTICIPANTS handling for the new format
                elif data.startswith("PARTICIPANTS|"):
                    # New Format: PARTICIPANTS|id1|name1|profile_url1||id2|name2|profile_url2||...
                    # Double pipe (||) separates each participant entry
                    data = data[len("PARTICIPANTS|"):]  # Remove the prefix
                    parts = data.split("||")
                    print("Received participants:", parts)
                    
                    # Reset the connected_users dictionary
                    self.connected_users = {}
                    
                    # Also track profile URLs for updating
                    profile_urls = {}
                    
                    for part in parts:
                        if not part:
                            continue
                            
                        segments = part.split("|")
                        if len(segments) >= 3:  # First segment is empty if part starts with |
                            user_id = segments[0]
                            user_name = segments[1]
                            profile_url = segments[2] if segments[2] else None
                            
                            self.connected_users[user_id] = user_name
                            
                            # Store profile URL if available
                            if profile_url:
                                profile_urls[user_id] = profile_url
                    
                    # Make sure we add ourselves if not already included
                    if self.user_id not in self.connected_users:
                        self.connected_users[self.user_id] = self.user_name
                    
                    # Update the UI first
                    self.update_participants_list()
                    
                    # Now fetch any profile pictures and update cards
                    for user_id, profile_url in profile_urls.items():
                        if user_id not in self.profile_pictures:
                            self.fetch_profile_picture(user_id, profile_url)
                            self.after(100, lambda uid=user_id: self.update_participant_card(uid))
            except Exception as e:
                print("Error receiving message:", e)
                break  # Exit the loop on error

    def redirect_to_dashboard(self):
        """Redirect user back to their dashboard"""
        self.destroy()  # Close the chat window

        try:
            if self.is_tutor:
                from tutor_panel import launch_tutor_panel
                launch_tutor_panel(self.sock, self.user_id, self.user_name, self.session_id,self.profile_pic_url)
            else:
                from student_panel import launch_student_panel
                launch_student_panel(self.sock, self.user_id, self.user_name, self.session_id,self.profile_pic_url)
        except Exception as e:
            print(f"Error redirecting to dashboard: {e}")
            # Handle error or reconnect if needed

    def end_chat(self):
        """
        End the current chat session (tutor only).
        Asks for confirmation before ending.
        """
        # Ask for confirmation to prevent accidental endings
        if messagebox.askyesno("End Chat", "Are you sure you want to end this chat session?"):
            try:
                # Send end chat command to the server
                send_data(self.sock,f"{self.session_id}|END_CHAT|{self.tutorial_id}")
                self.running = False  # Stop the message listener thread
                # Import before anything gets destroyed
                from tutor_panel import launch_tutor_panel
                
                # Cache all needed values
                sock = self.sock
                user_id = self.user_id
                user_name = self.user_name
                session_id = self.session_id
                profile_pic_url = self.profile_pic_url

                      # Destroy the window
                self.destroy()
                
                
                # Launch tutor panel directly - no after() method
                launch_tutor_panel(sock, user_id, user_name, session_id,profile_pic_url)
          
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to end chat: {str(e)}")

        # Add these methods to ChatRoom class
    def show_attendance(self):
        """Open the attendance window."""
        self.attendance_window = AttendanceWindow(
            self.window, 
            self.tutorial_id,
            self.chat_session_id
        )
        
        # Request initial attendance data
        self.request_attendance_update()

    def request_attendance_update(self):
        """Request updated attendance data from the server."""
        message = f"{self.session_id}|GET_ATTENDANCE|{self.chat_session_id}|{self.tutorial_id}"
        # Send the request to the server
        if self.sock:
            send_data(self.sock, message,timeout=0.1, flush=True)
        
    def create_chat_socket(self):
        try:
            # Create new socket
            self.chat_sock = create_tcp_socket()
            
            # Connect to server
            result = connect_to_server(self.chat_sock, HOST, PORT)
            if not result:
                raise Exception("Failed to connect to server")
                
            # Send session authentication
            auth_msg = f"SESSION_AUTH|{self.session_id}"
            send_data(self.chat_sock, auth_msg)
            
            # Wait for auth response
            auth_result = receive_data(self.chat_sock, timeout=5.0)
            if auth_result['status'] != SOCK_STATUS_OK:
                raise Exception("Auth failed - no response")
                
            auth_response = auth_result['data']
            if not auth_response.startswith("SUCCESS"):
                raise Exception(f"Auth failed: {auth_response}")
            
            # Now send CHAT_AUTH command with session ID
            chat_auth_msg = f"{self.session_id}|CHAT_AUTH|{self.tutorial_id}"
            send_data(self.chat_sock, chat_auth_msg)
            
            # Wait for chat auth confirmation
            chat_result = receive_data(self.chat_sock, timeout=5.0)
            if chat_result['status'] != SOCK_STATUS_OK:
                raise Exception("Chat auth failed - no response")
                
            chat_response = chat_result['data']
            if chat_response.startswith("CHAT_CONNECTED"):
                # Parse the remaining time from the response
                parts = chat_response.split("|")
                if len(parts) > 1:
                    try:
                        self.remaining_seconds = int(parts[1])
                        self.start_timer()
                    except ValueError:
                        self.display_message("System", "Error parsing timer value from server")
                
                self.display_message("System", "Connected to chat room")
                return True
            else:
                raise Exception(f"Chat auth failed: {chat_response}")
        except Exception as e:
            print(f"Chat socket error: {str(e)}")
            self.display_message("System", f"Error creating chat connection: {str(e)}")
            self.chat_sock = self.sock  # Fallback to main socket
            return False

    def start_timer(self):
        """Start the countdown timer."""
        if self.remaining_seconds > 0:
            self.timer_running = True
            self.update_timer_display()
            # Schedule next update
            self.window.after(self.timer_update_interval, self.update_timer)

    def update_timer(self):
        """Update the timer count and display."""
        if not self.timer_running:
            return
            
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.update_timer_display()
            
            # Schedule next update if time remains
            if self.remaining_seconds > 0:
                self.window.after(self.timer_update_interval, self.update_timer)
            else:
                # Timer reached zero
                self.timer_running = False
                self.timer_label.configure(
                    text="⏱️ Time's Up!",
                    text_color=COLORS["offline_text"]
                )
                self.timer_frame.configure(fg_color="#FFD0D0")  # Light red background
                
                # System message showing time's up
                self.display_message("System", "Chat session time has expired. The session will end shortly.")

    def update_timer_display(self):
        """Update the timer display with formatted time."""
        hours, remainder = divmod(self.remaining_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Change color based on time remaining
        if self.remaining_seconds <= 300:  # 5 minutes or less
            self.timer_label.configure(text_color=COLORS["offline_text"])
            self.timer_frame.configure(fg_color="#FFEEEE")  # Light pink warning color
        elif self.remaining_seconds <= 600:  # 10 minutes or less
            self.timer_label.configure(text_color="#FF6600")  # Orange
            
        time_format = f"⏱️ Time Remaining: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        self.timer_label.configure(text=time_format)

class AttendanceWindow(ctk.CTkToplevel):
    """Window to display attendance for a tutorial session."""
    
    def __init__(self, parent, tutorial_id, chat_session_id):
        super().__init__(parent)
        
        self.title(f"Attendance - {tutorial_id}")
        self.geometry("500x400")
        self.tutorial_id = tutorial_id
        self.chat_session_id = chat_session_id
        self.attendance_data = {}

        # Bring the window to the front
        self.lift()
        self.attributes("-topmost", True)
        self.after(10, lambda: self.attributes("-topmost", False))
        
        # Set window background color
        self.configure(fg_color=COLORS["hot_pink_bg"])
        
        # Create main frame with Y2K styling
        self.main_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["secondary_bg"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Add decorative header with Y2K styling
        header_frame = ctk.CTkFrame(
            self.main_frame, 
            fg_color=COLORS["turquoise"],
            corner_radius=12,
            border_width=2,
            border_color=COLORS["border_color"],
            height=40
        )
        header_frame.pack(fill='x', pady=(10, 20), padx=10)
        
        # Header title with stars for decoration
        header_label = ctk.CTkLabel(
            header_frame,
            text="✧ Attendance Record ✧",
            font=("Arial", 18, "bold"),
            text_color=COLORS["white"]
        )
        header_label.pack(pady=8)
        
        # Add Y2K styled refresh button at the top for better visibility
        self.refresh_btn = ctk.CTkButton(
            self.main_frame,
            text="✨ Refresh Attendance ✨",
            font=("Arial", 16, "bold"),
            fg_color=COLORS["bright_yellow"],
            hover_color=COLORS["folder_orange"],
            text_color=COLORS["text_color"],
            corner_radius=18,
            border_width=2,
            border_color=COLORS["border_color"],
            height=50,  # Increased height
            width=300,  # Set specific width to make it more prominent
            command=self.request_refresh
        )
        self.refresh_btn.pack(pady=(0, 15), padx=10)
        
        # Column headers with Y2K styling
        columns_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )
        columns_frame.pack(fill='x', pady=(0, 10), padx=15)
        
        ctk.CTkLabel(
            columns_frame, 
            text="Student", 
            font=("Arial", 16, "bold"),
            text_color=COLORS["text_color"]
        ).pack(side='left', padx=10)
        
        ctk.CTkLabel(
            columns_frame, 
            text="Status",
            font=("Arial", 16, "bold"),
            text_color=COLORS["text_color"]
        ).pack(side='left', padx=(80, 0))
        
        ctk.CTkLabel(
            columns_frame,
            text="Duration",
            font=("Arial", 16, "bold"),
            text_color=COLORS["text_color"]
        ).pack(side='right', padx=10)
        
        # Create scrollable frame for attendance records with Y2K styling
        self.attendance_frame = ctk.CTkScrollableFrame(
            self.main_frame,
            fg_color=COLORS["primary_bg"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        self.attendance_frame.pack(fill='both', expand=True, padx=10)
        
        # Initially empty - will be populated by update_attendance
        self.student_frames = {}
    
    def update_attendance(self, attendance_data):
        """Update the attendance display with new data."""
        # Store the data
        self.attendance_data = {item['student_id']: item for item in attendance_data}
        
        # Clear existing frames
        for frame in self.student_frames.values():
            frame.destroy()
        self.student_frames = {}
        
        # Create a frame for each student
        for item in attendance_data:
            student_id = item['student_id']
            student_name = item['student_name']
            is_present = item['is_present']
            duration = item['current_duration']
            
              # Add a rejoined indicator for students who have disconnected and rejoined
            rejoined = False
            if item['first_join_time'] > 0 and item['total_duration_seconds'] > 0 and is_present:
                rejoined = True
            
            # Create Y2K styled frame - with more distinct colors for presence status
                        # Create Y2K styled frame with colors based on status
            if rejoined:
                # Special Y2K-style for rejoined students
                bg_color = "#B4FFB4"  # Bright pink for rejoined
                border_color = "#FF00FF"  # Hot pink border
            elif is_present:
                bg_color = "#B4FFB4"  # Light green for present
                border_color = COLORS["online_text"]
            else:
                bg_color = "#FFACAC"  # Light red for absent
                border_color = COLORS["offline_text"]

            border_color = COLORS["online_text"] if is_present else COLORS["offline_text"]
            
            frame = ctk.CTkFrame(
                self.attendance_frame,
                fg_color=bg_color,
                corner_radius=12,
                border_width=2,
                border_color=border_color
            )
            frame.pack(fill='x', pady=4, padx=5)
            self.student_frames[student_id] = frame
             
            # Add student name with icon - special for rejoined
            if rejoined:
                icon_prefix = "✨👤✨ "  # Double sparkles for Y2K flair
                text_color = COLORS["online_text"]   
            else:
                icon_prefix = "👤 " 
                text_color = COLORS["online_text"] if is_present else COLORS["offline_text"]
                
            student_label = ctk.CTkLabel(
                frame,
                text=f"{icon_prefix}{student_name}",
                font=("Arial", 14, "bold"),
                text_color=text_color,
                width=150
            )
            student_label.pack(side='left', padx=10, pady=5)
            
            # Add status indicator with emoji - Y2K styled for rejoined
            if rejoined:
                status_text = "🌟 Rejoined! 🌟"  
            elif is_present:
                status_text = "🟢 Present"
            elif item['first_join_time'] > 0 and item['total_duration_seconds'] > 0 and not is_present:
                status_text = "🔴 Disconnected" 
            else:
                status_text = "🔴 Absent"
                
            status_label = ctk.CTkLabel(
                frame,
                text=status_text,
                text_color=text_color,
                font=("Arial", 14, "bold" if rejoined else "normal"),
                width=120  # Wider for rejoined text
            )
            status_label.pack(side='left', padx=10, pady=5)
            
            # Duration display with Y2K styling
            if rejoined:
                # Fancy calculator display for rejoined students
                duration_frame = ctk.CTkFrame(
                    frame,
                    fg_color=bg_color,
                    corner_radius=8,
                    border_width=1,
                    border_color=COLORS["border_color"],
                    width=90,
                    height=28  # Slightly taller
                )               
            elif is_present:
                duration_frame = ctk.CTkFrame(
                    frame,
                    fg_color=bg_color,
                    corner_radius=8,
                    border_width=1,
                    border_color=COLORS["border_color"],
                    width=90,
                    height=28
                )
            else:
                duration_frame = ctk.CTkFrame(
                    frame,
                    fg_color="#E0E0E0",  # Gray for absent
                    corner_radius=8,
                    border_width=1,
                    border_color=COLORS["border_color"],
                    width=90,
                    height=28
                )
            
            duration_frame.pack(side='right', padx=10, pady=5)
            duration_frame.pack_propagate(False)
            
            # Format duration with decoration for rejoined students
            duration_text = self.format_duration(duration)
            if rejoined:
                duration_text = f"★{duration_text}★"
                
            duration_label = ctk.CTkLabel(
                duration_frame,
                text=duration_text,
                font=("Courier", 14, "bold"),
                text_color= COLORS["text_color"] if rejoined else COLORS["text_color"] if is_present else "#777777"
            )
            duration_label.pack(expand=True)     

    def format_duration(self, seconds):
        """Format seconds into HH:MM:SS."""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    
    def request_refresh(self):
        """Send a request to refresh attendance data."""
        # This will be implemented in the parent class (ChatRoom)
        self.master.request_attendance_update()