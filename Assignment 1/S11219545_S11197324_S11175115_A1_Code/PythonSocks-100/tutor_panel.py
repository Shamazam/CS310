import customtkinter as ctk
from tkinter import simpledialog, messagebox
from PIL import Image
import os
from CustomSocket import (
    send_data, receive_data,
    SOCK_STATUS_OK, SOCK_STATUS_CLOSED, SOCK_STATUS_ERROR, SOCK_STATUS_TIMEOUT,close_socket
)

# Add this color palette after imports
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
    
    # Additional colors
    "hot_pink_bg": "#FF9DB0",     # Hot pink background
    "bright_yellow": "#FFDD4A",   # Bright yellow for buttons/accents
    "calculator_yellow": "#FFD700", # Calculator display yellow
    "lavender": "#C9A3FF",        # Lavender for secondary elements
    "folder_orange": "#FF9966",   # Folder orange
    "turquoise": "#4CD6C9",       # Turquoise for buttons
    "white": "#FFFFFF",           # White for text on dark backgrounds
    "online_text": "#0BDA51",     # Pastel green for online/present students
    "offline_text": "#FA5053",    # Pastel red for offline/absent students
}

class TutorialCard(ctk.CTkFrame):
    def __init__(self, parent, name, tutorial_id, view_callback, chat_callback, send_response_func=None, profile_pic_url=None):
        super().__init__(
            parent, 
            corner_radius=15,
            border_width=2, 
            border_color=COLORS["border_color"],
            height=80,
            fg_color=COLORS["secondary_bg"]
        )
        
        self.tutorial_id = tutorial_id
        self.name = name
        self.view_callback = view_callback
        self.chat_callback = chat_callback
        self.send_and_get_response = send_response_func

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

        # Tutorial Name with decorative stars
        self.label = ctk.CTkLabel(
            self, 
            text=f"✧ {name} ✧",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_color"]
        )
        self.label.grid(row=0, column=0, sticky="w", padx=20, pady=25)
        
        # Load icons
        script_dir = os.path.dirname(os.path.abspath(__file__))
        eye_img_path = os.path.join(script_dir, "eye.png")
        chat_img_path = os.path.join(script_dir, "chat.png")

        eye_img = ctk.CTkImage(light_image=Image.open(eye_img_path), size=(24, 24))
        chat_img = ctk.CTkImage(light_image=Image.open(chat_img_path), size=(24, 24))

        # Create styled button container
        self.icon_container = ctk.CTkFrame(
            self, 
            fg_color="transparent"
        )
        
        # Style the view button
        self.view_btn = ctk.CTkButton(
            self.icon_container, 
            text="View ✧", 
            image=eye_img,
            compound="left",
            width=100,
            height=40,
            corner_radius=18,
            fg_color=COLORS["button_color"],
            hover_color=COLORS["hover_color"],
            text_color=COLORS["text_color"],
            border_width=2,
            border_color=COLORS["border_color"],
            font=("Arial", 14, "bold"),
            command=self.view_students
        )
        
        # Style the chat button
        self.chat_btn = ctk.CTkButton(
            self.icon_container, 
            text="Chat ✧", 
            image=chat_img,
            compound="left",
            width=100,
            height=40,
            corner_radius=18, 
            fg_color=COLORS["bright_yellow"],
            hover_color=COLORS["folder_orange"],
            text_color=COLORS["text_color"],
            border_width=2,
            border_color=COLORS["border_color"],
            font=("Arial", 14, "bold"),
            command=self.start_chat
        )

        self.view_btn.pack(side="left", padx=5)
        self.chat_btn.pack(side="left", padx=5)
        self.icon_container.grid(row=0, column=1, sticky="e", padx=15)
        self.icon_container.grid_remove()

        self.bind_events()
        
    def update_chat_button(self):
        """Update the chat button text based on chat status"""
        response = self.send_and_get_response(f"CHECK_CHAT|{self.tutorial_id}")
        if response.startswith("CHAT_ACTIVE:"):
            self.chat_btn.configure(
                text="Join Chat ✧", 
                fg_color=COLORS["online_text"],
                hover_color="#21BA45"  # Slightly darker green
            )
        else:
            self.chat_btn.configure(
                text="Start Chat ✧", 
                fg_color=COLORS["bright_yellow"],
                hover_color=COLORS["folder_orange"]
            )

    def bind_events(self):
        widgets = [self, self.label, self.icon_container, self.view_btn, self.chat_btn]
        for widget in widgets:
            widget.bind("<Enter>", self.on_enter)
            widget.bind("<Leave>", self.on_leave)

    def on_enter(self, event=None):
        self.icon_container.grid()

    def on_leave(self, event=None):
        root = self.winfo_toplevel()
        hovered_widget = root.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())

        if hovered_widget not in (self, self.label, self.icon_container, self.view_btn, self.chat_btn):
            self.icon_container.grid_remove()

    def view_students(self):
        self.view_callback(self.tutorial_id, self.name)

    def start_chat(self):
        self.chat_callback(self.tutorial_id, self.name)

class TutorPanel(ctk.CTk):
    def __init__(self, sock, tutor_name, tutor_id, session_id, profile_pic_url=None):
        super().__init__()  # Initialize the root window
        self.sock = sock
        self.tutor_id = tutor_id
        self.tutor_name = tutor_name
        self.session_id = session_id
        self.profile_pic_url = profile_pic_url
        self.tutorial_cards = []

        self.title(f"Tutor Dashboard - {tutor_name}")
        self.geometry("800x700")  # Increased size for better aesthetic

        # Set light mode and configure window background
        ctk.set_appearance_mode("light")
        self.configure(fg_color=COLORS["primary_bg"])
        
        # Create main content frame
        main_frame = ctk.CTkFrame(
            self, 
            fg_color=COLORS["hot_pink_bg"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header frame with decorative border
        header_frame = ctk.CTkFrame(
            main_frame, 
            fg_color=COLORS["turquoise"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        header_frame.pack(pady=(20, 10), padx=20, fill="x")

        # Configure the header_frame for grid layout
        header_frame.columnconfigure(0, weight=1)  # Title column (expandable)
        header_frame.columnconfigure(1, weight=0)  # Button column (fixed size)

        # Add decorative title (using grid instead of pack)
        title_label = ctk.CTkLabel(
            header_frame, 
            text=f"✧ Welcome, Tutor {tutor_name}! ✧",
            font=("Arial", 24, "bold"),
            text_color=COLORS["white"]
        )
        title_label.grid(row=0, column=0, pady=10, sticky="w", padx=20)

        # Try to load the logout icon
        try:
            from PIL import Image
            logout_icon_path = "exit.png"
            logout_icon_image = Image.open(logout_icon_path)
            logout_icon = ctk.CTkImage(light_image=logout_icon_image, size=(24, 24))
            
            # Create icon button with Y2K styling
            logout_btn = ctk.CTkButton(
                header_frame,
                text="",
                image=logout_icon,
                fg_color=COLORS["hot_pink_bg"],
                hover_color=COLORS["folder_orange"],
                corner_radius=20,
                border_width=2,
                border_color=COLORS["border_color"],
                width=40,
                height=40,
                command=self.logout
            )
            logout_btn.grid(row=0, column=1, padx=15, pady=10, sticky="e")
        except Exception as e:
            print(f"Error loading logout icon: {e}")
            # Fallback to text button with Y2K styling
            logout_btn = ctk.CTkButton(
                header_frame,
                text="✧ Logout ✧",
                fg_color=COLORS["hot_pink_bg"],
                hover_color=COLORS["folder_orange"],
                text_color=COLORS["text_color"],
                corner_radius=15,
                border_width=2,
                border_color=COLORS["border_color"],
                width=100,
                height=32,
                command=self.logout
            )
            logout_btn.grid(row=0, column=1, padx=15, pady=10, sticky="e")

        # Profile section with styling
        profile_frame = ctk.CTkFrame(
            main_frame,
            fg_color=COLORS["secondary_bg"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        profile_frame.pack(pady=10, padx=20, fill="x")
        
        # Load and display profile picture
        profile_pic = self.load_profile_picture(profile_pic_url)
        if profile_pic:
            profile_pic_label = ctk.CTkLabel(profile_frame, image=profile_pic, text="")
            profile_pic_label.image = profile_pic
            profile_pic_label.pack(pady=10)
        
        # Display ID in a cute calculator-style display
        id_frame = ctk.CTkFrame(
            profile_frame,
            fg_color=COLORS["calculator_yellow"],
            corner_radius=10,
            border_width=2,
            border_color=COLORS["border_color"],
            height=40
        )
        id_frame.pack(padx=20, pady=(0, 10), fill="x")
        id_frame.pack_propagate(False)
        
        id_label = ctk.CTkLabel(
            id_frame, 
            text=f"Tutor ID: {tutor_id}",
            font=("Courier", 16, "bold"),
            text_color=COLORS["text_color"]
        )
        id_label.pack(expand=True)
        
        # Tutorials section header
        tutorials_header = ctk.CTkFrame(
            main_frame,
            fg_color=COLORS["lavender"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        tutorials_header.pack(pady=(20, 5), padx=20, fill="x")
        
        tutorials_label = ctk.CTkLabel(
            tutorials_header, 
            text="✧ My Tutorials ✧",
            font=("Arial", 20, "bold"),
            text_color=COLORS["text_color"]
        )
        tutorials_label.pack(pady=10)

        # Scrollable frame for tutorials with styled background
        self.scroll_frame = ctk.CTkScrollableFrame(
            main_frame, 
            width=700,
            height=380,
            fg_color=COLORS["primary_bg"],
            scrollbar_fg_color=COLORS["border_color"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Status label with styled background
        status_frame = ctk.CTkFrame(
            main_frame,
            fg_color=COLORS["system_msg_bg"],
            corner_radius=10,
            border_width=2,
            border_color=COLORS["border_color"],
            height=40
        )
        status_frame.pack(pady=10, padx=20, fill="x")
        status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            status_frame, 
            text="✧ Ready ✧",
            font=("Arial", 16),
            text_color=COLORS["text_color"]
        )
        self.status_label.pack(expand=True)
        
        # Load tutorials and start refresh timer
        self.tutorials = {}
        self.load_tutorials()
        self.start_refresh_timer()
    
    def load_default_profile(self):
        """Create a default profile picture"""
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (150, 150), color=COLORS["lavender"])
            draw = ImageDraw.Draw(img)
            
            # Draw a simple avatar
            draw.ellipse((30, 30, 120, 120), fill=COLORS["turquoise"])
            draw.ellipse((55, 55, 70, 70), fill='white')  # Left eye
            draw.ellipse((80, 55, 95, 70), fill='white')  # Right eye
            draw.arc((55, 80, 95, 110), start=0, end=180, fill='white', width=3)  # Smile
            
            return ctk.CTkImage(light_image=img, size=(150, 150))
        except Exception as e:
            print(f"Error creating default profile: {e}")
            return None

    def load_profile_picture(self, profile_pic_url):
        """Load a profile picture from a URL or use default"""
        if not profile_pic_url or not profile_pic_url.startswith(("http://", "https://")):
            return self.load_default_profile()

        try:
            import requests
            from PIL import Image
            from io import BytesIO

            response = requests.get(profile_pic_url)
            if response.status_code == 200:
                image_data = BytesIO(response.content)
                image = Image.open(image_data).resize((150, 150))
                return ctk.CTkImage(light_image=image, size=(150, 150))
            else:
                return self.load_default_profile()
        except Exception as e:
            print(f"Error loading profile picture: {e}")
            return self.load_default_profile()


    def start_refresh_timer(self):
        """Start a timer to refresh tutorial cards every 10 seconds"""
        self.refresh_tutorial_cards()
        self.after(10000, self.start_refresh_timer)  # 10 seconds

    def refresh_tutorial_cards(self):
        """Refresh all tutorial cards to update their status"""
        for card in self.tutorial_cards:
            card.update_chat_button()

    def send_and_get_response(self, command, *args):
        """
        Communicates with the server by sending commands and parameters using CustomSocket.
        
        Args:
            command (str): The command to execute (e.g., ASSIGNED_TUTORIALS)
            *args: Variable parameters for the command
            
        Returns:
            str: The server's response message
        """
        try:
            # Build message with proper formatting: session_id|command|arg1|arg2|...
            if args:
                message = f"{self.session_id}|{command}|" + "|".join(str(arg) for arg in args)
            else:
                message = f"{self.session_id}|{command}"
            
            print(f"Sending message: {message}")  # Debug print
            
            # Send message using CustomSocket's send_data function (with timeout)
            result = send_data(self.sock, message, timeout=5.0)
            if result['status'] != SOCK_STATUS_OK:
                return f"ERROR: Failed to send data (error code: {result['error']})"
            
            # Receive response using CustomSocket's receive_data function (with timeout)
            result = receive_data(self.sock, buffer_size=8192, timeout=10.0)
            if result['status'] != SOCK_STATUS_OK:
                if result['status'] == SOCK_STATUS_TIMEOUT:
                    return "ERROR: Server response timeout"
                elif result['status'] == SOCK_STATUS_CLOSED:
                    return "ERROR: Connection closed by server"
                else:
                    return f"ERROR: Failed to receive response (error code: {result['error']})"
                
            return result['data']
        except Exception as e:
            print(f"Socket communication error: {str(e)}")
            return f"ERROR: {str(e)}"

    def load_tutorials(self):
        response = self.send_and_get_response("ASSIGNED_TUTORIALS")
        
        # Clear any existing tutorials first
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.tutorial_cards = []
            
        if response.startswith("ERROR:"):
            self.status_label.configure(
                text=f"✧ Error: {response[6:]} ✧", 
                text_color=COLORS["offline_text"]
            )
            return
                
        if response == "NONE":
            self.status_label.configure(
                text="✧ No tutorials assigned ✧", 
                text_color=COLORS["offline_text"]
            )
            # Add empty state illustration or message
            empty_label = ctk.CTkLabel(
                self.scroll_frame,
                text="No tutorials currently assigned to you.\nCheck back later!",
                font=("Arial", 18),
                text_color=COLORS["text_color"]
            )
            empty_label.pack(pady=50)
            return

        # Display tutorials with the new styling
        self.status_label.configure(
            text=f"✧ {len(response.split('|'))} tutorials found ✧", 
            text_color=COLORS["online_text"]
        )
        
        for line in response.split('|'):
            tid, name = line.split("::")
            self.tutorials[tid] = name
            card = TutorialCard(
                self.scroll_frame, 
                name, 
                tid,
                view_callback=self.view_students,
                chat_callback=self.ask_duration_and_start_chat,
                send_response_func=self.send_and_get_response
            )
            card.pack(fill="x", padx=10, pady=8)
            self.tutorial_cards.append(card)

    def view_students(self, tutorial_id, tutorial_name):
        response = self.send_and_get_response("TUTORIAL_STUDENTS", tutorial_id)
        
        if response.startswith("ERROR:"):
            messagebox.showerror("Error", response)
            return
                
        if response == "NONE":
            # Create styled message box
            no_students_window = ctk.CTkToplevel(self)
            no_students_window.title(f"Students - {tutorial_name}")
            no_students_window.geometry("400x250")
            no_students_window.configure(fg_color=COLORS["primary_bg"])
            no_students_window.attributes('-topmost', True)  # Make window appear on top
            no_students_window.focus_force()  # Force focus to this window
            
            frame = ctk.CTkFrame(
                no_students_window,
                fg_color=COLORS["secondary_bg"],
                corner_radius=15,
                border_width=2,
                border_color=COLORS["border_color"]
            )
            frame.pack(padx=20, pady=20, fill="both", expand=True)
            
            message = ctk.CTkLabel(
                frame,
                text="✧ No students assigned to this tutorial ✧",
                font=("Arial", 16, "bold"),
                text_color=COLORS["text_color"]
            )
            message.pack(pady=50)
            
            ok_btn = ctk.CTkButton(
                frame,
                text="OK ✧",
                font=("Arial", 16, "bold"),
                height=40,
                corner_radius=18,
                fg_color=COLORS["button_color"],
                hover_color=COLORS["hover_color"],
                text_color=COLORS["text_color"],
                border_width=2,
                border_color=COLORS["border_color"],
                command=no_students_window.destroy
            )
            ok_btn.pack(pady=20)
            
            # Ensure the window stays on top after placement
            no_students_window.after(100, lambda: no_students_window.lift())
        else:
            # Create styled student list window
            students_window = ctk.CTkToplevel(self)
            students_window.title(f"Students - {tutorial_name}")
            students_window.geometry("600x500")
            students_window.configure(fg_color=COLORS["primary_bg"])
            students_window.attributes('-topmost', True)  # Make window appear on top
            students_window.focus_force()  # Force focus to this window
            
            frame = ctk.CTkFrame(
                students_window,
                fg_color=COLORS["secondary_bg"],
                corner_radius=15,
                border_width=2,
                border_color=COLORS["border_color"]
            )
            frame.pack(padx=20, pady=20, fill="both", expand=True)
            
            # Header
            header = ctk.CTkFrame(
                frame,
                fg_color=COLORS["turquoise"],
                corner_radius=15,
                border_width=2,
                border_color=COLORS["border_color"]
            )
            header.pack(padx=10, pady=10, fill="x")
            
            title = ctk.CTkLabel(
                header,
                text=f"✧ Students in {tutorial_name} ✧",
                font=("Arial", 18, "bold"),
                text_color=COLORS["white"]
            )
            title.pack(pady=10)
            
            # Student list
            student_frame = ctk.CTkScrollableFrame(
                frame,
                fg_color=COLORS["primary_bg"],
                corner_radius=15,
                border_width=2,
                border_color=COLORS["border_color"],
                height=350
            )
            student_frame.pack(padx=10, pady=10, fill="both", expand=True)
            
            # Add each student as a card
            for i, line in enumerate(response.split("|")):
                student_id, student_name = line.split("::")
                
                student_card = ctk.CTkFrame(
                    student_frame,
                    fg_color=COLORS["user_msg_bg"] if i % 2 == 0 else COLORS["others_msg_bg"],
                    corner_radius=10,
                    border_width=1,
                    border_color=COLORS["border_color"]
                )
                student_card.pack(fill="x", padx=5, pady=5)
                
                icon_label = ctk.CTkLabel(
                    student_card,
                    text="👤",
                    font=("Arial", 18),
                    text_color=COLORS["text_color"]
                )
                icon_label.pack(side="left", padx=10, pady=10)
                
                name_label = ctk.CTkLabel(
                    student_card,
                    text=f"{student_name}",
                    font=("Arial", 16, "bold"),
                    text_color=COLORS["text_color"]
                )
                name_label.pack(side="left", padx=10, pady=10)
                
                id_label = ctk.CTkLabel(
                    student_card,
                    text=f"ID: {student_id}",
                    font=("Arial", 14),
                    text_color=COLORS["text_color"]
                )
                id_label.pack(side="right", padx=10, pady=10)
            
            # Close button
            close_btn = ctk.CTkButton(
                frame,
                text="Close ✧",
                font=("Arial", 16, "bold"),
                height=40,
                corner_radius=18,
                fg_color=COLORS["button_color"],
                hover_color=COLORS["hover_color"],
                text_color=COLORS["text_color"],
                border_width=2,
                border_color=COLORS["border_color"],
                command=students_window.destroy
            )
            close_btn.pack(pady=10)
            
            # Ensure the window stays on top
            students_window.after(100, lambda: students_window.lift())
    
    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            
            # Close the socket connection
            try:
                close_socket(self.sock)
                print("Socket closed successfully")
            except Exception as e:
                print(f"Error closing socket: {e}")
            
            # Close the current window
            self.destroy()
            
            # Import here to avoid circular imports
            from client_login import LoginWindow
            
            # Launch the login window
            root = ctk.CTk()
            login_app = LoginWindow(root)
            root.mainloop()
    
    def ask_duration_and_start_chat(self, tutorial_id, tutorial_name):
        try:
            # Check if chat is already active for this tutorial
            response = self.send_and_get_response(f"CHECK_CHAT|{tutorial_id}")
            
            if response.startswith("CHAT_ACTIVE:"):
                # Chat already exists, extract session ID
                chat_session_id = response.split(":")[1]
                
                
                # Create styled confirmation dialog
                confirm_dialog = ctk.CTkToplevel(self)
                confirm_dialog.title("Chat Active")
                confirm_dialog.geometry("180x120")
                confirm_dialog.configure(fg_color=COLORS["primary_bg"])
                confirm_dialog.attributes('-topmost', True)
                confirm_dialog.focus_force()
                
                # Make dialog modal
                confirm_dialog.transient(self)
                confirm_dialog.grab_set()
                
                # Store result
                confirm_dialog.result = False
                
                frame = ctk.CTkFrame(
                    confirm_dialog,
                    fg_color=COLORS["secondary_bg"],
                    corner_radius=15,
                    border_width=2,
                    border_color=COLORS["border_color"]
                )
                frame.pack(padx=20, pady=20, fill="both", expand=True)
                
                title = ctk.CTkLabel(
                    frame,
                    text="✧ Chat Already Active ✧",
                    font=("Arial", 18, "bold"),
                    text_color=COLORS["text_color"]
                )
                title.pack(pady=(20, 5))
                
                message = ctk.CTkLabel(
                    frame,
                    text=f"A chat session is already active for\n{tutorial_name}.\nWould you like to rejoin?",
                    font=("Arial", 14),
                    text_color=COLORS["text_color"]
                )
                message.pack(pady=(5, 20))
                
                btn_frame = ctk.CTkFrame(
                    frame,
                    fg_color="transparent"
                )
                btn_frame.pack(pady=10)
                
                def on_yes():
                    confirm_dialog.result = True
                    confirm_dialog.destroy()
                    
                def on_no():
                    confirm_dialog.result = False
                    confirm_dialog.destroy()
                    
                yes_btn = ctk.CTkButton(
                    btn_frame,
                    text="Yes ✧",
                    font=("Arial", 16, "bold"),
                    width=100,
                    height=40,
                    corner_radius=18,
                    fg_color=COLORS["online_text"],
                    hover_color="#21BA45",
                    text_color=COLORS["white"],
                    border_width=2,
                    border_color=COLORS["border_color"],
                    command=on_yes
                )
                yes_btn.pack(side="left", padx=10)
                
                no_btn = ctk.CTkButton(
                    btn_frame,
                    text="No ✧",
                    font=("Arial", 16, "bold"),
                    width=100,
                    height=40,
                    corner_radius=18,
                    fg_color=COLORS["offline_text"],
                    hover_color="#D32F2F",
                    text_color=COLORS["white"],
                    border_width=2,
                    border_color=COLORS["border_color"],
                    command=on_no
                )
                no_btn.pack(side="left", padx=10)

                # Center the confirm dialog on screen
                confirm_dialog.update_idletasks()  # Make sure dimensions are updated
                width = confirm_dialog.winfo_width()
                height = confirm_dialog.winfo_height()
                x = (confirm_dialog.winfo_screenwidth() // 2) - (width // 2)
                y = (confirm_dialog.winfo_screenheight() // 2) - (height // 2)
                confirm_dialog.geometry(f"{width}x{height}+{x}+{y}")
                
                # Wait for dialog to close
                self.wait_window(confirm_dialog)
                
                if confirm_dialog.result:
                    # Join existing chat
                    join_response = self.send_and_get_response(f"JOIN_CHAT|{tutorial_id}")
                    if join_response.startswith("CHAT_JOINED:"):
                        parts = join_response.split(":")
                        self.redirect_to_chat_room(tutorial_id, 0, chat_session_id, self.profile_pic_url)
                    else:
                        self.status_label.configure(
                            text=f"✧ {join_response} ✧", 
                            text_color=COLORS["offline_text"]
                        )
                return
            
            # No active chat, ask for duration and start a new one
            duration = self.show_duration_dialog(tutorial_name)
            if duration is None:
                return

            response = self.send_and_get_response(f"START_CHAT|{tutorial_id}|{duration}")
            if response.startswith("CHAT_STARTED:"):
                chat_session_id = response.split(":")[1]
                self.redirect_to_chat_room(tutorial_id, duration, chat_session_id, self.profile_pic_url)
            else:
                self.status_label.configure(
                    text=f"✧ {response} ✧", 
                    text_color=COLORS["offline_text"]
                )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_duration_dialog(self, tutorial_name):
            """Show a styled dialog to ask for chat duration"""
            dialog = ctk.CTkToplevel(self)
            dialog.title("Chat Duration")
            dialog.geometry("400x250")
            dialog.configure(fg_color=COLORS["primary_bg"])
            dialog.attributes('-topmost', True)
            dialog.focus_force()
            
            # Make dialog modal
            dialog.transient(self)
            dialog.grab_set()
            
            frame = ctk.CTkFrame(
                dialog,
                fg_color=COLORS["secondary_bg"],
                corner_radius=15,
                border_width=2,
                border_color=COLORS["border_color"]
            )
            frame.pack(padx=20, pady=20, fill="both", expand=True)
            
            title = ctk.CTkLabel(
                frame,
                text=f"✧ Enter Chat Duration ✧",
                font=("Arial", 18, "bold"),
                text_color=COLORS["text_color"]
            )
            title.pack(pady=(20, 5))
            
            subtitle = ctk.CTkLabel(
                frame,
                text=f"For tutorial: {tutorial_name}",
                font=("Arial", 14),
                text_color=COLORS["text_color"]
            )
            subtitle.pack(pady=(0, 20))
            
            # Duration input with calculator-style display
            duration_var = ctk.StringVar(value="30")
            duration_frame = ctk.CTkFrame(
                frame,
                fg_color=COLORS["calculator_yellow"],
                corner_radius=10,
                border_width=2,
                border_color=COLORS["border_color"]
            )
            duration_frame.pack(padx=50, fill="x")
            
            duration_entry = ctk.CTkEntry(
                duration_frame,
                textvariable=duration_var,
                font=("Courier", 18, "bold"),
                justify="center",
                fg_color=COLORS["calculator_yellow"],
                text_color=COLORS["text_color"],
                border_width=0
            )
            duration_entry.pack(pady=10, padx=10, fill="x")
            
            # Buttons frame
            btn_frame = ctk.CTkFrame(
                frame,
                fg_color="transparent"
            )
            btn_frame.pack(pady=20)
            
            # Store result in dialog object
            dialog.result = None
            
            def on_ok():
                try:
                    val = int(duration_var.get())
                    if 5 <= val <= 120:
                        dialog.result = val
                        dialog.destroy()
                    else:
                        messagebox.showwarning("Invalid Input", "Please enter a value between 5 and 120 minutes.")
                except ValueError:
                    messagebox.showwarning("Invalid Input", "Please enter a valid number.")
            
            def on_cancel():
                dialog.result = None
                dialog.destroy()
            
            # OK button
            ok_btn = ctk.CTkButton(
                btn_frame,
                text="OK ✧",
                font=("Arial", 16, "bold"),
                width=100,
                height=40,
                corner_radius=18,
                fg_color=COLORS["online_text"],
                hover_color="#21BA45",
                text_color=COLORS["white"],
                border_width=2,
                border_color=COLORS["border_color"],
                command=on_ok
            )
            ok_btn.pack(side="left", padx=10)
            
            # Cancel button
            cancel_btn = ctk.CTkButton(
                btn_frame,
                text="Cancel ✧",
                font=("Arial", 16, "bold"),
                width=100,
                height=40,
                corner_radius=18,
                fg_color=COLORS["offline_text"],
                hover_color="#D32F2F",
                text_color=COLORS["white"],
                border_width=2,
                border_color=COLORS["border_color"],
                command=on_cancel
            )
            cancel_btn.pack(side="left", padx=10)
            
            # Wait for dialog to close
            self.wait_window(dialog)
            return dialog.result
   

    def redirect_to_chat_room(self, tutorial_id, duration, chat_session_id,profile_pic_url=None):
       # Use the instance profile_pic_url if none provided
        if profile_pic_url is None:
            profile_pic_url = self.profile_pic_url
            
        self.destroy()  # Close the tutor panel
        from chat_room import ChatRoom
        chat = ChatRoom(
            self.sock,
            self.tutor_id,
            self.tutor_name,
            tutorial_id,
            self.tutorials[tutorial_id],
            self.session_id,
            is_tutor=True,
            tutor_id=self.tutor_id,
            chat_session_id=chat_session_id,  # Fixed: added comma here
            profile_pic_url=profile_pic_url   # Fixed: proper parameter passing
        )
        
        chat.mainloop()          

    def on_closing(self):
  
     self.running = False  # Stop 
     self.sock.close()  # Close the socket
     self.destroy()


def launch_tutor_panel(s, name, user_id, session_id,profile_pic_url):
    panel = TutorPanel(s, name, user_id, session_id,profile_pic_url)
    panel.mainloop()