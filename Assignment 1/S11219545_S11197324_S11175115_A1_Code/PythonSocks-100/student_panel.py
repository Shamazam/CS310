import customtkinter as ctk
from tkinter import simpledialog, messagebox
from PIL import Image
import os
     # Add this import at the top
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
    
    # Additional colors from the image
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
                text="No Active Chats✧", 
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



class StudentPanel(ctk.CTk):
    def __init__(self, sock, student_id, student_name, session_id, profile_pic_url=None):
        super().__init__()  # Initialize the root window
        self.sock = sock
        self.student_id = student_id
        self.student_name = student_name
        self.session_id = session_id
        self.profile_pic_url = profile_pic_url
        self.tutorial_cards = []

        self.title(f"Student Dashboard - {student_name}")
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


                #Configure the header_frame for grid layout
        header_frame.columnconfigure(0, weight=1)  # Title column (expandable)
        header_frame.columnconfigure(1, weight=0)  # Button column (fixed size)

        # Add decorative title (using grid instead of pack)
        title_label = ctk.CTkLabel(
            header_frame, 
            text=f"✧ Welcome, {student_name}! ✧",
            font=("Arial", 24, "bold"),
            text_color=COLORS["white"]
        )
        title_label.grid(row=0, column=0, pady=10, sticky="w", padx=20)

           # Load the logout icon
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
            self.logout_btn = ctk.CTkButton(
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
            self.logout_btn.pack(pady=10)



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
            text=f"Student ID: {student_id}",
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

    def on_closing(self):
        self.running = False  # Stop 
        self.sock.close()  # Close the socket
        self.destroy()

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
        
        for line in response.split("|"):
            tid, name = line.split("::")
            self.tutorials[tid] = name
            card = TutorialCard(
                self.scroll_frame, 
                name, 
                tid,
                view_callback=self.view_students,
                chat_callback=self.join_chat,
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
            # Create styled student list window with increased size
            students_window = ctk.CTkToplevel(self)
            students_window.title(f"Students - {tutorial_name}")
            students_window.geometry("600x500")  # Increased from 500x400
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
            
            # Student list with increased height
            student_frame = ctk.CTkScrollableFrame(
                frame,
                fg_color=COLORS["primary_bg"],
                corner_radius=15,
                border_width=2,
                border_color=COLORS["border_color"],
                height=350  # Increased from 250
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
            
            # Ensure the window stays on top even after placement
            students_window.after(100, lambda: students_window.lift())
    
    def join_chat(self, tutorial_id, tutorial_name):
        response = self.send_and_get_response("JOIN_CHAT", tutorial_id)
        if response.startswith("ERROR:"):
            messagebox.showerror("Error", response)
            return
            
                # In the join_chat method
        if response.startswith("CHAT_JOINED:"):
            parts = response.split(":")
            tutor_id = parts[1]
            chat_session_id = parts[2]
            self.destroy()

            # Create the chat room first, before destroying the panel
            try:
                from chat_room import ChatRoom
                chat = ChatRoom(
                    self.sock,
                    self.student_id,
                    self.student_name,
                    tutorial_id,
                    tutorial_name,
                    self.session_id,
                    is_tutor=False,
                    tutor_id=tutor_id,
                    chat_session_id=chat_session_id, # Pass the chat session ID
                    profile_pic_url=self.profile_pic_url   # Fixed: proper parameter passing

                )

                chat.mainloop()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to join chat room: {str(e)}")
        else:
            messagebox.showerror("Error", response)


def launch_student_panel(sock, student_id, name, session_id,profile_pic_url):
    panel = StudentPanel(sock, student_id, name, session_id,profile_pic_url)
    panel.mainloop()