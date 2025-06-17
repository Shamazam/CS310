from tkinter import messagebox
import customtkinter as ctk  # Custom themed Tkinter for modern UI elements
from CustomSocket import (
    send_data, receive_data,
    SOCK_STATUS_OK, SOCK_STATUS_CLOSED, SOCK_STATUS_ERROR, SOCK_STATUS_TIMEOUT,close_socket
)
ctk.set_default_color_theme("blue")  # Set the default color scheme

# Add Y2K-inspired color palette
COLORS = {
    "primary_bg": "#AEE9F9",      # Pastel blue
    "secondary_bg": "#FFD6F6",    # Pastel pink
    "system_msg_bg": "#FFF3C7",   # Light yellow
    "user_msg_bg": "#FFB6B9",     # Pastel pink
    "others_msg_bg": "#E0C3FC",   # Pastel purple
    "button_color": "#4CD6C9",    # Turquoise 
    "border_color": "#8A2BE2",    # Purple
    "text_color": "#333333",      # Dark text
    "hover_color": "#8A7BF7",     # Slightly darker purple for hover
    "hot_pink_bg": "#FF9DB0",     # Hot pink background
    "bright_yellow": "#FFDD4A",   # Bright yellow for buttons/accents
    "folder_orange": "#FF9966",   # Folder orange
    "turquoise": "#4CD6C9",       # Turquoise for buttons
    "white": "#FFFFFF",           # White for text on dark backgrounds
}
ctk.set_appearance_mode('Light')


class AdminPanel(ctk.CTk):
    """
    Admin Panel GUI for managing users and tutorials.
    This panel allows administrators to:
    - Create new users (students and tutors)
    - Create new tutorials 
    - Assign users to tutorials
    """
    def __init__(self, sock, admin_name, session_id, profile_pic_url=None):
        super().__init__()
        self.title(f"Admin Panel - {admin_name}")
        self.geometry("600x600")
        self.sock = sock
        self.session_id = session_id
        self.profile_pic_url = profile_pic_url
        self.admin_name = admin_name
        
        # Set window background color
        self.configure(fg_color=COLORS["primary_bg"])
        
        # Header frame with Y2K styling
        header_frame = ctk.CTkFrame(
            self, 
            fg_color=COLORS["secondary_bg"], 
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        header_frame.pack(pady=20, padx=20, fill="x")
    
    # ...rest of initialization code
        
            # Create logout frame with Y2K styling
        logout_frame = ctk.CTkFrame(
            header_frame, 
            fg_color="transparent"
        )
        logout_frame.pack(side="right", padx=10, fill="y")

        # Load the logout icon
        try:
            from PIL import Image
            logout_icon_path = "exit.png"
            logout_icon_image = Image.open(logout_icon_path)
            logout_icon = ctk.CTkImage(light_image=logout_icon_image, size=(24, 24))
            
            # Create icon button with Y2K styling
            self.logout_btn = ctk.CTkButton(
                logout_frame,
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
            self.logout_btn.pack(pady=10)
            
            
        except Exception as e:
            print(f"Error loading logout icon: {e}")
            # Fallback to text button with Y2K styling
            self.logout_btn = ctk.CTkButton(
                logout_frame,
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
            self.logout_btn.pack(pady=10)

            # Load and display profile picture with decorative frame
        profile_pic = self.load_profile_picture(profile_pic_url)
        if profile_pic:
            # Create decorative frame for profile picture
            profile_frame = ctk.CTkFrame(
                header_frame,
                fg_color=COLORS["hot_pink_bg"],
                corner_radius=75,  # Makes it circular
                border_width=3,
                border_color=COLORS["border_color"]
            )
            profile_frame.pack(pady=(10, 5))
            
            # Add the profile picture
            profile_pic_label = ctk.CTkLabel(profile_frame, image=profile_pic, text="")
            profile_pic_label.image = profile_pic
            profile_pic_label.pack(padx=5, pady=5)

        # Display Y2K-style greeting with stars
        greeting_label = ctk.CTkLabel(
            header_frame, 
            text=f"✧ Hi {admin_name}! ✧", 
            font=("Arial", 22, "bold"),
            text_color=COLORS["text_color"]
        )
        greeting_label.pack(pady=(10, 15))
        
                # Create a decorative title for the admin panel
        title_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["turquoise"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"],
            height=40
        )
        title_frame.pack(fill="x", pady=(5, 15), padx=20)

        # Add title with decoration
        title_label = ctk.CTkLabel(
            title_frame,
            text="✧ Admin Control Panel ✧",
            font=("Arial", 18, "bold"),
            text_color=COLORS["white"]
        )
        title_label.pack(pady=8)

        # Create a scrollable frame with Y2K styling
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self, 
            width=560, 
            height=420,
            fg_color=COLORS["secondary_bg"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        self.scrollable_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Create the three main sections of the admin panel inside the scrollable frame
        self.create_user_section()
        self.create_tutorial_section()
        self.create_assignment_section()
        
        # Track notification windows
        self.notification_window = None
        self.after_id = None

    # Add this method to the AdminPanel class

    def logout(self):
        """Logout the admin and redirect to the login screen."""
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

    def load_profile_picture(self, profile_pic_url):
        """
        Load a profile picture from a URL.
        
        Parameters:
            profile_pic_url (str): URL of the profile picture.
        
        Returns:
            ctk.CTkImage: Loaded profile picture as a CTkImage, or None if invalid.
        """
        if not profile_pic_url or not profile_pic_url.startswith(("http://", "https://")):
            print("Invalid profile picture URL")
            print("URL:", profile_pic_url)
            return None

        try:
            import requests
            from PIL import Image
            from io import BytesIO

            response = requests.get(profile_pic_url)
            if response.status_code == 200:
                image_data = BytesIO(response.content)
                image = Image.open(image_data).resize((150, 150))  # Resize to 150x150
                return ctk.CTkImage(light_image=image, size=(150, 150))
        except Exception as e:
            print(f"Error loading profile picture: {e}")
        return None

    def create_user_section(self):
        # Create frame with Y2K styling
        frame = ctk.CTkFrame(
            self.scrollable_frame,
            fg_color=COLORS["primary_bg"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        frame.pack(pady=10, padx=10, fill="x")

        # Section header with Y2K styling
        header_frame = ctk.CTkFrame(
            frame,
            fg_color=COLORS["turquoise"],
            corner_radius=12,
            border_width=0
        )
        header_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header_frame, 
            text="✧ Create User ✧", 
            font=("Arial", 16, "bold"),
            text_color=COLORS["white"]
        ).pack(pady=5)

        # User inputs with Y2K styling
        self.entry_user_id = ctk.CTkEntry(
            frame, 
            placeholder_text="User ID",
            height=35,
            corner_radius=12,
            border_width=2,
            border_color=COLORS["border_color"],
            fg_color="white"
        )
        self.entry_user_id.pack(pady=5, padx=15, fill="x")

        self.entry_user_name = ctk.CTkEntry(
            frame, 
            placeholder_text="Name",
            height=35,
            corner_radius=12,
            border_width=2,
            border_color=COLORS["border_color"],
            fg_color="white"
        )
        self.entry_user_name.pack(pady=5, padx=15, fill="x")

        self.entry_user_pw = ctk.CTkEntry(
            frame, 
            placeholder_text="Password", 
            show="*",
            height=35,
            corner_radius=12,
            border_width=2,
            border_color=COLORS["border_color"],
            fg_color="white"
        )
        self.entry_user_pw.pack(pady=5, padx=15, fill="x")

        # Role selector with Y2K styling
        self.user_role_option = ctk.CTkOptionMenu(
            frame, 
            values=["student", "tutor"],
            fg_color=COLORS["bright_yellow"],
            button_color=COLORS["folder_orange"],
            button_hover_color=COLORS["border_color"],
            dropdown_fg_color=COLORS["secondary_bg"],
            text_color=COLORS["text_color"],
            dropdown_text_color=COLORS["text_color"],
            dropdown_hover_color=COLORS["hot_pink_bg"],
            width=200,
            height=35,
            corner_radius=12
        )
        self.user_role_option.set("student")
        self.user_role_option.pack(pady=5, padx=15)

        # Create user button with Y2K styling
        ctk.CTkButton(
            frame, 
            text="✧ Create User ✧",
            font=("Arial", 16, "bold"),
            fg_color=COLORS["button_color"],
            hover_color=COLORS["hover_color"],
            text_color=COLORS["text_color"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"],
            height=40,
            command=self.create_user
        ).pack(pady=10, padx=15, fill="x")

    def create_tutorial_section(self):
        # Create frame with Y2K styling
        frame = ctk.CTkFrame(
            self.scrollable_frame,
            fg_color=COLORS["primary_bg"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        frame.pack(pady=10, padx=10, fill="x")

        # Section header with Y2K styling
        header_frame = ctk.CTkFrame(
            frame,
            fg_color=COLORS["turquoise"],
            corner_radius=12,
            border_width=0
        )
        header_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header_frame, 
            text="✧ Create Tutorial ✧", 
            font=("Arial", 16, "bold"),
            text_color=COLORS["white"]
        ).pack(pady=5)

        # Tutorial inputs with Y2K styling
        self.entry_tutorial_id = ctk.CTkEntry(
            frame, 
            placeholder_text="Tutorial ID",
            height=35,
            corner_radius=12,
            border_width=2,
            border_color=COLORS["border_color"],
            fg_color="white"
        )
        self.entry_tutorial_id.pack(pady=5, padx=15, fill="x")

        self.entry_tutorial_name = ctk.CTkEntry(
            frame, 
            placeholder_text="Tutorial Name",
            height=35,
            corner_radius=12,
            border_width=2,
            border_color=COLORS["border_color"],
            fg_color="white"
        )
        self.entry_tutorial_name.pack(pady=5, padx=15, fill="x")

        # Create tutorial button with Y2K styling
        ctk.CTkButton(
            frame, 
            text="✧ Create Tutorial ✧",
            font=("Arial", 16, "bold"),
            fg_color=COLORS["button_color"],
            hover_color=COLORS["hover_color"],
            text_color=COLORS["text_color"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"],
            height=40,
            command=self.create_tutorial
        ).pack(pady=10, padx=15, fill="x")
    def create_assignment_section(self):
        # Create frame with Y2K styling
        frame = ctk.CTkFrame(
            self.scrollable_frame,
            fg_color=COLORS["primary_bg"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"]
        )
        frame.pack(pady=10, padx=10, fill="x")

        # Section header with Y2K styling
        header_frame = ctk.CTkFrame(
            frame,
            fg_color=COLORS["turquoise"],
            corner_radius=12,
            border_width=0
        )
        header_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header_frame, 
            text="✧ Assign User to Tutorial ✧", 
            font=("Arial", 16, "bold"),
            text_color=COLORS["white"]
        ).pack(pady=5)

        # Assignment inputs with Y2K styling
        self.entry_assign_user = ctk.CTkEntry(
            frame, 
            placeholder_text="User ID",
            height=35,
            corner_radius=12,
            border_width=2,
            border_color=COLORS["border_color"],
            fg_color="white"
        )
        self.entry_assign_user.pack(pady=5, padx=15, fill="x")

        self.entry_assign_tutorial = ctk.CTkEntry(
            frame, 
            placeholder_text="Tutorial ID",
            height=35,
            corner_radius=12,
            border_width=2,
            border_color=COLORS["border_color"],
            fg_color="white"
        )
        self.entry_assign_tutorial.pack(pady=5, padx=15, fill="x")

        # Assign button with Y2K styling
        ctk.CTkButton(
            frame, 
            text="✧ Assign User ✧",
            font=("Arial", 16, "bold"),
            fg_color=COLORS["bright_yellow"],
            hover_color=COLORS["folder_orange"],
            text_color=COLORS["text_color"],
            corner_radius=15,
            border_width=2,
            border_color=COLORS["border_color"],
            height=40,
            command=self.assign_user
        ).pack(pady=10, padx=15, fill="x")
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
    
    def create_user(self):
        """
        Handles the user creation process when the Create User button is clicked.
        
        Validates input fields, sends the user data to the server,
        and updates the UI based on the server's response.
        """
        # Get values from the input fields
        uid = self.entry_user_id.get()
        name = self.entry_user_name.get()
        pw = self.entry_user_pw.get()
        role = self.user_role_option.get()

        # Validate that all fields have values
        if not uid or not name or not pw:
            self.show_popup_notification("Fill all user fields", "info")
            return

        try:
            # Send CREATE_USER command with user details to the server
            response = self.send_and_get_response("CREATE_USER", uid, name, pw, role)
            
            if response == "USER_CREATED":
                # Clear fields and show success message
                self.entry_user_id.delete(0, "end")
                self.entry_user_name.delete(0, "end")
                self.entry_user_pw.delete(0, "end")
                self.user_role_option.set("student")
                self.show_popup_notification("✅ User created successfully!", "success")
            elif response.startswith("FAIL:"):
                # Show specific error message received from server
                error_msg = response.split("FAIL:", 1)[1]
                self.show_popup_notification(f"❌ Error: {error_msg}", "error")
            else:
                # Show unexpected response
                self.show_popup_notification(f"❓ {response}", "info")

        except Exception as e:
            # Handle any exceptions during the process
            self.show_popup_notification(f"❌ Error: {str(e)}", "error")

    def create_tutorial(self):
        """
        Handles the tutorial creation process when the Create Tutorial button is clicked.
        
        Validates input fields, sends the tutorial data to the server,
        and updates the UI based on the server's response.
        """
        # Get values from the input fields
        tid = self.entry_tutorial_id.get()
        tname = self.entry_tutorial_name.get()

        # Validate that all fields have values
        if not tid or not tname:
            self.show_popup_notification("Fill all tutorial fields", "input")
            return

        try:
            # Send CREATE_TUTORIAL command with tutorial details to the server
            response = self.send_and_get_response("CREATE_TUTORIAL", tid, tname)

            if response == "TUTORIAL_CREATED":
                # Clear fields and show success message
                self.entry_tutorial_id.delete(0, "end")
                self.entry_tutorial_name.delete(0, "end")
                self.show_popup_notification("✅ Tutorial created successfully!", "success")
            elif response.startswith("FAIL:"):
                # Show specific error message received from server
                error_msg = response.split("FAIL:", 1)[1]
                self.show_popup_notification(f"❌ Error: {error_msg}", "error")
            else:
                # Show unexpected response
                self.show_popup_notification(f"❓ {response}", "info")

        except Exception as e:
            # Handle any exceptions during the process
            self.show_popup_notification(f"❌ Error: {str(e)}", "error")

    def assign_user(self):
        """
        Handles the user-to-tutorial assignment process when the Assign button is clicked.
        
        Validates input fields, sends the assignment data to the server,
        and updates the UI based on the server's response.
        
        This function supports assigning both students and tutors to tutorials,
        with server-side validation to ensure proper assignments.
        """
        # Get values from the input fields
        uid = self.entry_assign_user.get()
        tid = self.entry_assign_tutorial.get()

        # Validate that all fields have values
        if not uid or not tid:
            self.show_popup_notification("Fill both assignment fields", "info")
            return

        try:
            # Send ASSIGN command with user ID and tutorial ID to the server
            response = self.send_and_get_response("ASSIGN", uid, tid)

            if response == "ASSIGNED":
                # Clear fields and show success message
                self.entry_assign_user.delete(0, "end")
                self.entry_assign_tutorial.delete(0, "end")
                self.show_popup_notification("✅ User assigned successfully!", "success")
            elif response.startswith("FAIL:"):
                # Show specific error message received from server
                error_msg = response.split("FAIL:", 1)[1]
                self.show_popup_notification(f"❌ Error: {error_msg}", "error")
            else:
                # Show unexpected response
                self.show_popup_notification(f"❓ {response}", "info")

        except Exception as e:
            # Handle any exceptions during the process
            self.show_popup_notification(f"❌ Error: {str(e)}", "error")
    
    # Add a new method for showing popup notifications
    def show_popup_notification(self, message, type_="info"):
        """Show a popup notification above all other elements with Y2K styling."""
        # Close any existing notification
        if self.notification_window and self.notification_window.winfo_exists():
            self.notification_window.destroy()
        
        # Cancel any existing auto-close timer
        if self.after_id:
            self.after_cancel(self.after_id)
        
        # Define colors based on notification type but with Y2K aesthetic
        colors = {
            "success": {"bg": COLORS["primary_bg"], "fg": COLORS["text_color"], "border": COLORS["button_color"], "icon": "✅"},
            "error": {"bg": COLORS["hot_pink_bg"], "fg": COLORS["text_color"], "border": COLORS["border_color"], "icon": "❌"},
            "info": {"bg": COLORS["secondary_bg"], "fg": COLORS["text_color"], "border": COLORS["bright_yellow"], "icon": "ℹ️"}
        }
        
        color = colors.get(type_, colors["info"])
        
        # Create popup window
        popup = ctk.CTkToplevel(self)
        popup.title("")
        popup.geometry("400x80")
        popup.resizable(False, False)
        popup.attributes('-topmost', True)
        
        # Calculate center position
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 40
        popup.geometry(f"+{x}+{y}")
        
        # Remove window decorations for cleaner look
        popup.overrideredirect(True)
        
        # Create frame with Y2K styling
        frame = ctk.CTkFrame(
            popup,
            fg_color=color["bg"],
            border_width=2,
            border_color=color["border"],
            corner_radius=15
        )
        frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Add message with decoration
        label = ctk.CTkLabel(
            frame,
            text=f"✧ {message} ✧",
            text_color=color["fg"],
            font=("Arial", 14, "bold")
        )
        label.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Auto-close after 3 seconds
        self.notification_window = popup
        self.after_id = self.after(3000, popup.destroy)


def launch_admin_panel(sock, name, session_id, profile_pic_url=None):
    """
    Creates and launches the admin panel application.
    
    Args:
        sock (socket): The socket connection to the server
        name (str): The admin's name to display in the window title
        session_id (str): The session ID for authenticating requests
        
    This function is called from the login page after successful admin authentication.
    """
    app = AdminPanel(sock, name, session_id, profile_pic_url)  # Create admin panel with session info
    app.mainloop()  # Start the GUI event loop