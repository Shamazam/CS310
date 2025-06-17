import customtkinter as ctk
import os
from PIL import Image
# Import enhanced socket functions from CustomSocket
from CustomSocket import (
    create_tcp_socket_with_options, perform_tcp_handshake,
    send_data, receive_data, close_socket,
    SOCK_STATUS_OK, SOCK_STATUS_TIMEOUT, SOCK_STATUS_CLOSED, SOCK_STATUS_ERROR
)

# Add this color palette for Y2K/aesthetic styling
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
    "hot_pink_bg": "#FF9DB0",     # Hot pink background
    "bright_yellow": "#FFDD4A",   # Bright yellow for buttons/accents
    "calculator_yellow": "#FFD700", # Calculator display yellow
    "lavender": "#C9A3FF",        # Lavender for secondary elements
    "folder_orange": "#FF9966",   # Folder orange
    "turquoise": "#4CD6C9",       # Turquoise for buttons
    "white": "#FFFFFF",           # White for text on dark backgrounds
    "online_text": "#0BDA51",     # Pastel green for online/present students
    "offline_text": "#FA5053",    # Pastel red for offline/absent students
    "secondary_bg_light":"#FFE9FA",
    "night_blue" :"#343B5C",      # Dark blue-purple from night sky
    "deep_purple": "#292550",     # Deeper purple background tone
    "night_purple": "#6A5B99"    # Mid-tone purple from image
}

# Add these colors from the background image
COLORS.update({
    # Main color scheme from image
    "lofi_deep_blue": "#1A3E4C",      # Deep teal-blue of the night sky
    "lofi_night_sky": "#091D28",      # Darkest blue of night sky
    "lofi_window_glow": "#23778C",    # Teal blue glow from window
    "lofi_bright_teal": "#4FCCF0",    # Bright cyan highlights
    
    # Pink/purple tones
    "lofi_headphone_pink": "#FF6B8B", # Bright pink of headphones
    "lofi_soft_pink": "#FFB0C1",      # Light pink desk items
    "lofi_lavender": "#A191B0",       # Soft lavender clothing
    "lofi_violet": "#9D8AA5",         # Soft violet highlights
    "lofi_coral": "#FF9F8A",          # Soft orange-pink accents
    
    # Additional useful tones
    "lofi_skin": "#ECBCB4",           # Warm beige skin tone
    "lofi_cat_blue": "#303E5C",       # Blue-gray of the cat silhouette
    "lofi_desk_purple": "#604C72",    # Purple tone of desk elements
})

# Server connection details
HOST = '127.0.0.1'  # Address of the server (same machine in this case)
PORT = 5090        # Port number (must match the server's port)

def try_login():
    """
    Attempts to log in with the provided credentials.
    This function is called when the login button is clicked.
    """
    # Get the values entered by the user
    user_id = entry_id.get()    # Get text from ID field
    password = entry_pw.get()   # Get text from password field

    try:
        # Create a socket with optimized settings for interactive application
        s = create_tcp_socket_with_options(
            nodelay=True,      # Disable Nagle's algorithm for responsive login
            reuse_addr=False,  # Not needed for client
            keepalive=True,    # Enable keepalive to detect server disconnection
            recv_buffer=8192,  # 8KB receive buffer
            send_buffer=8192   # 8KB send buffer
        )
        
        if not s:
            status_label.configure(text="⚠️ Failed to create socket", text_color=COLORS["offline_text"])
            return
            
        # Connect to the server with custom TCP handshake parameters
        status_label.configure(text="⌛ Connecting to server...", text_color=COLORS["hot_pink_bg"])
        if not perform_tcp_handshake(s, HOST, PORT, syn_retry=3, timeout_sec=5):
            status_label.configure(text="⚠️ Failed to connect to server", text_color=COLORS["offline_text"])
            close_socket(s, cleanup=True)
            return
        
        status_label.configure(text="⌛ Authenticating...", text_color=COLORS["hot_pink_bg"])
        # Format login data as "user_id|password"
        login_data = f"{user_id}|{password}"
        
        # Send login data to server with 5-second timeout
        result = send_data(s, login_data, timeout=5.0)
        if result['status'] != SOCK_STATUS_OK:
            status_label.configure(text="⚠️ Failed to send login data", text_color=COLORS["offline_text"])
            close_socket(s, cleanup=True)
            return

        # Wait for server response with 10-second timeout
        result = receive_data(s, buffer_size=4096, timeout=10.0)
        if result['status'] != SOCK_STATUS_OK:
            if result['status'] == SOCK_STATUS_TIMEOUT:
                status_label.configure(text="⚠️ Server response timeout", text_color=COLORS["offline_text"])
            else:
                status_label.configure(text="⚠️ Connection error", text_color=COLORS["offline_text"])
            close_socket(s, cleanup=True)
            return
            
        response = result['data']
        
        # Check if login was successful
        if response.startswith("SUCCESS"):
            print(response)
            # Parse response which contains role, name, and session_id
            # Format: SUCCESS:role:name:session_id
            parts = response.split("|")
            if len(parts) < 5:
                status_label.configure(text="⚠️ Invalid server response", text_color=COLORS["offline_text"])
                close_socket(s, cleanup=True)
                return

            role, name, session_id, profile_pic_url = parts[1:5]

            # Show success message
            status_label.configure(text=f"✅ Logged in as {name} ({role})", text_color=COLORS["online_text"])

            # Close the login window
            app.destroy()

            # Open the appropriate panel based on user role
            if role == "admin":
                # Import and launch admin panel
                from admin_panel import launch_admin_panel
                launch_admin_panel(s, name, session_id, profile_pic_url)
                
            elif role == "tutor":
                # Import and launch tutor panel
                from tutor_panel import launch_tutor_panel
                launch_tutor_panel(s, name, user_id, session_id, profile_pic_url)

            elif role == "student":
                # Import and launch student panel
                from student_panel import launch_student_panel
                launch_student_panel(s, user_id, name, session_id, profile_pic_url)
               
        else:
            # Login failed, parse and show specific error message if available
            error_message = response.split(":", 1)[1] if ":" in response else "Login failed"
            status_label.configure(text=f"❌ {error_message}", text_color=COLORS["offline_text"])
            close_socket(s, cleanup=True)  # Close the socket connection

    except Exception as e:
        # Handle connection errors
        status_label.configure(text="⚠️ Error connecting to server", text_color=COLORS["offline_text"])
        print("Connection error:", e)


# Set up the appearance of the app
ctk.set_appearance_mode("light")      # Use light theme to match student panel
ctk.set_default_color_theme("blue")   # Use blue color scheme

# After creating the app
app = ctk.CTk()
app.geometry("600x600")  # Set the initial size
app.title("Tutorial Management System")  # Set the window title
app.resizable(False, False)  # Prevent resizing (width, height)
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bg_path = os.path.join(script_dir, "bg.png")
    bg_image = ctk.CTkImage(light_image=Image.open(bg_path), size=(600, 600))
    
    # Create a label with background image
    bg_label = ctk.CTkLabel(app, image=bg_image, text="")
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
except Exception as e:
    print(f"Error loading background image: {e}")

# Update the outer frame to match the lofi aesthetic from the image
outer_frame = ctk.CTkFrame(
    app,
    corner_radius=18,
    border_width=0,
    fg_color=COLORS["lofi_desk_purple"]  # Purple tone from desk elements
)
outer_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.83, relheight=0.73)

# Update main frame with a deep blue from the night sky
main_frame = ctk.CTkFrame(
    app,
    corner_radius=15,
    border_width=2,
    border_color=COLORS["lofi_headphone_pink"],  # Pink from headphones as border
    fg_color=COLORS["lofi_night_sky"]  # Dark blue from night sky
)
main_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.7)

# Add a title label with decorative elements
title_label = ctk.CTkLabel(
    main_frame, 
    text="✧ 🔐 Login ✧", 
    font=("Arial", 28, "bold"),
    text_color=COLORS["text_color"]
)
title_label.pack(pady=(30, 20))

# Update text color for better visibility on dark background
title_label.configure(text_color=COLORS["lofi_soft_pink"])  # Light pink for title

# Create styled input fields
entry_id = ctk.CTkEntry(
    main_frame, 
    placeholder_text="User ID", 
    width=280,
    height=45,
    corner_radius=10,
    border_width=2,
    border_color=COLORS["border_color"],
    font=("Arial", 16)
)
entry_id.pack(pady=15)

# Create the password input field (shows dots instead of characters)
entry_pw = ctk.CTkEntry(
    main_frame, 
    placeholder_text="Password", 
    show="*", 
    width=280,
    height=45,
    corner_radius=10,
    border_width=2,
    border_color=COLORS["border_color"],
    font=("Arial", 16)
)
entry_pw.pack(pady=15)

# Create the login button with Y2K styling
login_btn = ctk.CTkButton(
    main_frame, 
    text="✧ Login ✧",
    font=("Arial", 18, "bold"),
    width=200,
    height=50,
    corner_radius=18,
    fg_color=COLORS["button_color"],
    hover_color=COLORS["hover_color"],
    text_color=COLORS["text_color"],
    border_width=2,
    border_color=COLORS["border_color"],
    command=try_login
)
login_btn.pack(pady=25)

# Create a styled frame for status messages
status_frame = ctk.CTkFrame(
    main_frame,
    fg_color=COLORS["system_msg_bg"],
    corner_radius=10,
    border_width=2,
    border_color=COLORS["border_color"],
    height=40
)
status_frame.pack(pady=15, padx=20, fill="x")
status_frame.pack_propagate(False)

# Create a label to show status messages
status_label = ctk.CTkLabel(
    status_frame, 
    text="✧ Enter your credentials ✧",
    font=("Arial", 16),
    text_color=COLORS["text_color"]
)
status_label.pack(expand=True)
# Update input fields to match the aesthetic
entry_id.configure(
    border_color=COLORS["lofi_violet"],
    fg_color=COLORS["lofi_cat_blue"],
    text_color=COLORS["white"],
    placeholder_text_color=COLORS["lofi_soft_pink"]
)

entry_pw.configure(
    border_color=COLORS["lofi_violet"],
    fg_color=COLORS["lofi_cat_blue"],
    text_color=COLORS["white"],
    placeholder_text_color=COLORS["lofi_soft_pink"]
)

# Update login button to match headphone pink
login_btn.configure(
    fg_color=COLORS["lofi_headphone_pink"],
    hover_color=COLORS["lofi_coral"],
    text_color=COLORS["white"],
    border_color=COLORS["lofi_bright_teal"]
)

# Update status frame
status_frame.configure(
    fg_color=COLORS["lofi_window_glow"],
    border_color=COLORS["lofi_bright_teal"]
)

# Update status label
status_label.configure(
    text_color=COLORS["white"]
)

# Start the main event loop
# This keeps the application running and responsive to user input
app.mainloop()
