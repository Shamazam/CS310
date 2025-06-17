import ctypes  # Allows Python to call C functions and use C data types
import struct  # Helps with converting between Python values and C struct representations
import threading  # Enables running multiple threads of execution in parallel
import time  # Provides time-related functions like delays

# ---------------------- SETUP AND CONSTANTS ----------------------

# Load the Windows Socket API library (Winsock)
# This gives us access to the low-level networking functions in Windows
ws2_32 = ctypes.WinDLL('ws2_32.dll')

# ----- Socket Constants -----
# These constants are used throughout the socket API

# Address Family - AF_INET means we're using IPv4 networking
AF_INET = 2

# Socket Type - SOCK_STREAM means we're using TCP (reliable, connection-oriented)
SOCK_STREAM = 1

# Protocol - IPPROTO_TCP specifies we're using the TCP protocol
IPPROTO_TCP = 6

# Special value indicating an invalid socket
INVALID_SOCKET = -1

# ----- Socket Option Levels -----
# These specify which protocol level the option applies to

# SOL_SOCKET - Options at socket level (not protocol specific)
SOL_SOCKET = 0xFFFF

# IPPROTO_IP - Options for the IP protocol
IPPROTO_IP = 0

# IPPROTO_TCP - Options for the TCP protocol (already defined above)
# IPPROTO_TCP = 6

# ----- Socket Options -----
# These are the specific options we can set at different levels

# TCP protocol options
TCP_NODELAY = 0x0001   # Disable Nagle's algorithm (improves responsiveness)
TCP_KEEPALIVE = 0x0003 # Set time between keepalive packets (in milliseconds)
TCP_KEEPINTVL = 0x0010 # Interval between keepalives


# IP protocol options
IP_TTL = 0x4  # Time to live - how many router hops before packet is dropped
IP_TOS = 0x3  # Type of service - priority of the connection

# Socket level options
SO_RCVBUF = 0x1002     # Size of receive buffer
SO_SNDBUF = 0x1001     # Size of send buffer
SO_REUSEADDR = 0x0004  # Allow reusing local addresses
SO_KEEPALIVE = 0x0008  # Enable/disable keepalive packets
SO_LINGER = 0x0080     # Control what happens when socket is closed with data waiting to be sent

# Windows-specific control code for configuring keepalive behavior
SIO_KEEPALIVE_VALS = ctypes.c_ulong(0x98000004)

# Add these constants at the top with the other socket constants
FIONBIO = 0x8004667E  # Command to set non-blocking mode
SOCKET_ERROR = -1
WSAEWOULDBLOCK = 10035  # Error code when operation would block

# Add these constants just after your other constants
SO_RCVTIMEO = 0x1006  # Socket option for receive timeout
SO_SNDTIMEO = 0x1005  # Socket option for send timeout
WSAETIMEDOUT = 10060  # Error code for timeout

# Status codes for socket operations
SOCK_STATUS_OK = 0       # Operation completed successfully
SOCK_STATUS_TIMEOUT = 1  # Operation timed out
SOCK_STATUS_CLOSED = 2   # Connection was closed
SOCK_STATUS_ERROR = 3    # An error occurred

# Define how the inet_ntop function should be called and what it returns
# This function converts a network address to a string (e.g., "127.0.0.1")
ws2_32.inet_ntop.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
ws2_32.inet_ntop.restype = ctypes.c_char_p

# ---------------------- DATA STRUCTURES ----------------------

# WSAData structure - Stores Windows Socket initialization information
class WSAData(ctypes.Structure):
    _fields_ = [
        # Version of Winsock requested
        ("wVersion", ctypes.c_ushort),
        # Highest version of Winsock supported
        ("wHighVersion", ctypes.c_ushort),
        # Description string of the Winsock implementation
        ("szDescription", ctypes.c_char * 257),
        # System status string
        ("szSystemStatus", ctypes.c_char * 129),
        # Maximum number of sockets allowed
        ("iMaxSockets", ctypes.c_ushort),
        # Maximum datagram size
        ("iMaxUdpDg", ctypes.c_ushort),
        # Pointer to vendor-specific information
        ("lpVendorInfo", ctypes.c_char_p)
    ]

# Structure for IPv4 socket addresses
class SockaddrIn(ctypes.Structure):
    _fields_ = [
        # Address family (AF_INET = IPv4)
        ("sin_family", ctypes.c_short),
        # Port number in network byte order
        ("sin_port", ctypes.c_ushort),
        # IP address as a 32-bit integer
        ("sin_addr", ctypes.c_ulong),
        # Padding to make the structure the right size
        ("sin_zero", ctypes.c_char * 8)
    ]

# Structure representing a TCP packet header
class TCPHeader(ctypes.Structure):
    _fields_ = [
        # Port sending the data
        ("source_port", ctypes.c_uint16),
        # Port receiving the data
        ("dest_port", ctypes.c_uint16),
        # Sequence number for ordered delivery
        ("seq_number", ctypes.c_uint32),
        # Acknowledgment number for reliability
        ("ack_number", ctypes.c_uint32),
        # Size of the TCP header in 32-bit words
        ("data_offset", ctypes.c_uint8),
        # Control flags (SYN, ACK, FIN, etc.)
        ("flags", ctypes.c_uint8),
        # Flow control window size
        ("window", ctypes.c_uint16),
        # Error checking value
        ("checksum", ctypes.c_uint16),
        # Pointer to urgent data (rarely used)
        ("urgent_ptr", ctypes.c_uint16)
    ]

# Structure for configuring the socket linger behavior
# (controls what happens when closing a socket with pending data)
class LingerStruct(ctypes.Structure):
    _fields_ = [
        # Whether linger is enabled (1) or disabled (0)
        ("l_onoff", ctypes.c_int16),
        # How many seconds to wait for data to be sent when closing
        ("l_linger", ctypes.c_int16)
    ]

# Windows-specific structure for configuring keepalive parameters
class KeepaliveVals(ctypes.Structure):
    _fields_ = [
        # Enable (1) or disable (0) keepalive
        ("onoff", ctypes.c_ulong),
        # Time in milliseconds before sending first keepalive
        ("keepalivetime", ctypes.c_ulong),
        # Interval in milliseconds between keepalives if no response
        ("keepaliveinterval", ctypes.c_ulong)
    ]

# ---------------------- BASIC SOCKET FUNCTIONS ----------------------

def create_tcp_socket():
    """
    Create a new TCP socket by initializing Winsock and creating a socket.
    
    Returns:
        A socket handle if successful, None if failed
    """
    # Initialize Winsock API
    wsadata = WSAData()
    
    # Initialize Winsock with version 2.2 (0x0202)
    result = ws2_32.WSAStartup(0x0202, ctypes.byref(wsadata))
    
    # Check if initialization succeeded
    if result != 0:
        handle_error(f"WSAStartup failed with error: {result}")
        return None
    
    # Create a new socket
    # Parameters: 
    # - AF_INET: IPv4 address family
    # - SOCK_STREAM: TCP socket type
    # - IPPROTO_TCP: TCP protocol
    # - None: No protocol-specific template
    # - 0, 0: Default flags
    sock = ws2_32.WSASocketA(AF_INET, SOCK_STREAM, IPPROTO_TCP, None, 0, 0)
    
    # Check if socket creation succeeded
    if sock == INVALID_SOCKET:
        error = ws2_32.WSAGetLastError()
        handle_error(f"Socket creation failed with error: {error}")
        ws2_32.WSACleanup()  # Clean up Winsock
        return None
    
    return sock

def connect_to_server(sock, ip, port):
    """
    Connect a socket to a server at the specified IP address and port.
    
    Parameters:
        sock: Socket handle
        ip: Server IP address (e.g., "127.0.0.1")
        port: Server port number
        
    Returns:
        True if connection succeeded, False otherwise
    """
    # Create address structure for the server
    server_addr = SockaddrIn()
    server_addr.sin_family = AF_INET  # IPv4
    
    # Convert port number to network byte order
    # Network byte order is big-endian, which may be different from your computer's byte order
    server_addr.sin_port = struct.unpack('H', struct.pack('!H', port))[0]
    
    # Convert IP address string to 32-bit integer
    server_addr.sin_addr = ctypes.c_ulong(ws2_32.inet_addr(ip.encode()))
    
    # Attempt to connect to the server
    # We pass the address by reference (byref) so C can modify it if needed
    result = ws2_32.connect(sock, ctypes.byref(server_addr), ctypes.sizeof(server_addr))
    
    # Check if connection succeeded
    if result != 0:
        error = ws2_32.WSAGetLastError()
        handle_error(f"Connect failed with error: {error}")
        return False
    
    return True

def set_non_blocking(sock, non_blocking=True):
    """
    Set a socket to non-blocking or blocking mode.
    
    Parameters:
        sock: Socket handle
        non_blocking: True for non-blocking, False for blocking
        
    Returns:
        True if successful, False otherwise
    """
    mode = ctypes.c_ulong(1 if non_blocking else 0)
    result = ws2_32.ioctlsocket(sock, FIONBIO, ctypes.byref(mode))
    
    if result != 0:
        error = ws2_32.WSAGetLastError()
        handle_error(f"Failed to set socket blocking mode, error: {error}")
        return False
    return True

def send_data(sock, data, timeout=None, flush=False):
    """
    Send string data over a connected socket with timeout support.
    
    Parameters:
        sock: Socket handle
        data: String data to send
        timeout: Timeout in seconds, or None for blocking operation
        flush: If True, disable Nagle's algorithm for this send
        
    Returns:
        Dictionary with status information
    """
    # If flush requested, temporarily disable Nagle's algorithm
    if flush:
        # Store original TCP_NODELAY setting
        nodelay_val = ctypes.c_int(0)
        opt_size = ctypes.c_int(ctypes.sizeof(nodelay_val))
        ws2_32.getsockopt(sock, IPPROTO_TCP, TCP_NODELAY, 
                         ctypes.byref(nodelay_val), ctypes.byref(opt_size))
        
        # Enable TCP_NODELAY to disable Nagle's algorithm
        new_val = ctypes.c_int(1)
        ws2_32.setsockopt(sock, IPPROTO_TCP, TCP_NODELAY,
                         ctypes.byref(new_val), ctypes.sizeof(new_val))
    
    # Convert string to bytes
    encoded_data = data.encode()
    total_bytes = len(encoded_data)
    
    # Set timeout if specified
    original_timeout = None
    if timeout is not None:
        # Windows uses milliseconds for timeouts
        timeout_ms = int(timeout * 1000)
        timeout_struct = struct.pack('LL', timeout_ms, 0)
        
        # Store original timeout for restoration later
        original_timeout = ctypes.create_string_buffer(8)
        original_len = ctypes.c_int(8)
        
        # Get original timeout
        ws2_32.getsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, 
                         original_timeout, ctypes.byref(original_len))
        
        # Set new timeout
        ws2_32.setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, 
                         timeout_struct, len(timeout_struct))
    
    # Send the data
    bytes_sent = ws2_32.send(sock, encoded_data, total_bytes, 0)
    
    # Restore original timeout if we changed it
    if timeout is not None and original_timeout:
        ws2_32.setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, 
                         original_timeout, original_len)
    
    # Restore original TCP_NODELAY setting if needed
    if flush:
        ws2_32.setsockopt(sock, IPPROTO_TCP, TCP_NODELAY,
                         ctypes.byref(nodelay_val), ctypes.sizeof(nodelay_val))
    
    # Handle result
    if bytes_sent == SOCKET_ERROR:
        error = ws2_32.WSAGetLastError()
        if error == WSAETIMEDOUT:
            return {'status': SOCK_STATUS_TIMEOUT, 'bytes_sent': 0, 'error': error}
        else:
            return {'status': SOCK_STATUS_ERROR, 'bytes_sent': 0, 'error': error}
    elif bytes_sent == 0:
        return {'status': SOCK_STATUS_CLOSED, 'bytes_sent': 0, 'error': 0}
    else:
        return {'status': SOCK_STATUS_OK, 'bytes_sent': bytes_sent, 'error': 0}

def receive_data(sock, buffer_size=1024, timeout=None):
    """
    Receive data from a connected socket with timeout support.
    
    Parameters:
        sock: Socket handle
        buffer_size: Maximum amount of data to receive at once
        timeout: Timeout in seconds, or None for blocking operation
        
    Returns:
        Dictionary with status information or simple string for backward compatibility
    """
    # Create buffer for received data
    buffer = ctypes.create_string_buffer(buffer_size)
    
    # Set timeout if specified
    original_timeout = None
    if timeout is not None:
        # Windows uses milliseconds for timeouts
        timeout_ms = int(timeout * 1000)
        timeout_struct = struct.pack('LL', timeout_ms, 0)
        
        # Store original timeout for restoration later
        original_timeout = ctypes.create_string_buffer(8)
        original_len = ctypes.c_int(8)
        
        # Get original timeout
        ws2_32.getsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, 
                         original_timeout, ctypes.byref(original_len))
        
        # Set new timeout
        ws2_32.setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, 
                         timeout_struct, len(timeout_struct))
    
    # Receive data
    bytes_received = ws2_32.recv(sock, buffer, buffer_size, 0)
    
    # Restore original timeout if we changed it
    if timeout is not None and original_timeout:
        ws2_32.setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, 
                         original_timeout, original_len)
    
    # Process result
    if bytes_received == SOCKET_ERROR:
        error = ws2_32.WSAGetLastError()
        if error == WSAETIMEDOUT:
            return {'status': SOCK_STATUS_TIMEOUT, 'data': "", 'error': error}
        else:
            return {'status': SOCK_STATUS_ERROR, 'data': "", 'error': error}
    elif bytes_received == 0:
        return {'status': SOCK_STATUS_CLOSED, 'data': "", 'error': 0}
    else:
        data = buffer.raw[:bytes_received].decode()
        return {'status': SOCK_STATUS_OK, 'data': data, 'error': 0}

def bind_socket(sock, ip, port):
    """
    Bind a socket to a local IP address and port.
    This is necessary for server sockets to listen for connections.
    
    Parameters:
        sock: Socket handle
        ip: Local IP address to bind to, or None for all interfaces
        port: Port number to bind to
        
    Returns:
        True if binding succeeded, False otherwise
    """
    # Create address structure
    addr = SockaddrIn()
    addr.sin_family = AF_INET  # IPv4
    
    # Convert port to network byte order
    addr.sin_port = struct.unpack('H', struct.pack('!H', port))[0]
    
    # Set the IP address
    if ip:
        # Bind to the specific IP address
        addr.sin_addr = ctypes.c_ulong(ws2_32.inet_addr(ip.encode()))
    else:
        # Bind to all interfaces (0.0.0.0)
        addr.sin_addr = ctypes.c_ulong(0)  # INADDR_ANY
    
    # Bind the socket to the address
    result = ws2_32.bind(sock, ctypes.byref(addr), ctypes.sizeof(addr))
    
    # Check if binding succeeded
    if result != 0:
        error = ws2_32.WSAGetLastError()
        handle_error(f"Bind failed with error: {error}")
        return False
    
    return True

def listen_for_connections(sock, backlog=100):
    """
    Put a socket into listening mode to accept incoming connections.
    
    Parameters:
        sock: Socket handle
        backlog: Maximum number of pending connections in queue
        
    Returns:
        True if the operation succeeded, False otherwise
    """
    # Put socket in listening mode
    result = ws2_32.listen(sock, backlog)
    
    # Check if operation succeeded
    if result != 0:
        error = ws2_32.WSAGetLastError()
        handle_error(f"Listen failed with error: {error}")
        return False
    
    return True

def accept_connection(server_socket):
    """
    Accept an incoming connection on a listening socket.
    
    Parameters:
        server_socket: The listening socket handle
        
    Returns:
        Tuple (client_socket, address_info) if successful, None otherwise
        where address_info is a tuple (ip_str, port)
    """
    try:
        # Structure to store client address information
        client_addr = SockaddrIn()
        
        # Variable to store the size of address structure
        addr_len = ctypes.c_int(ctypes.sizeof(client_addr))
        
        # Accept a connection
        # This call blocks until a client connects
        client_sock = ws2_32.accept(server_socket, 
                                  ctypes.byref(client_addr), 
                                  ctypes.byref(addr_len))
        
        # Check if accept succeeded
        if client_sock == INVALID_SOCKET:
            error = ws2_32.WSAGetLastError()
            handle_error(f"Accept failed with error: {error}")
            return None
            
        # Convert the IP address from integer format to string format (e.g., "127.0.0.1")
        # We extract each byte from the 32-bit integer and join with dots
        addr = client_addr.sin_addr
        ip_bytes = [(addr >> (i * 8)) & 0xff for i in range(4)]
        ip_str = '.'.join(str(b) for b in reversed(ip_bytes))
        
        # Convert the port from network byte order to host byte order
        port = socket_ntohs(client_addr.sin_port)
        
        # Return the new socket and the client's address information
        return (client_sock, (ip_str, port))
        
    except Exception as e:
        handle_error(f"Exception in accept_connection: {e}")
        return None

def get_peer_name(socket):
    """
    Get the address information of the remote end of a connected socket.
    
    Parameters:
        socket: Connected socket handle
        
    Returns:
        Tuple (ip_str, port) if successful, None otherwise
    """
    try:
        # Structure to store remote address information
        client_addr = SockaddrIn()
        
        # Variable to store size of address structure
        addr_len = ctypes.c_int(ctypes.sizeof(client_addr))
        
        # Get the peer name (remote address)
        result = ws2_32.getpeername(socket, 
                                  ctypes.byref(client_addr), 
                                  ctypes.byref(addr_len))
        
        # Check if operation succeeded
        if result != 0:
            error = ws2_32.WSAGetLastError()
            handle_error(f"getpeername failed with error: {error}")
            return None
            
        # Convert IP address from integer to string
        addr = client_addr.sin_addr
        ip_bytes = [(addr >> (i * 8)) & 0xff for i in range(4)]
        ip_str = '.'.join(str(b) for b in reversed(ip_bytes))
        
        # Convert port from network byte order to host byte order
        port = socket_ntohs(client_addr.sin_port)
        
        return (ip_str, port)
        
    except Exception as e:
        handle_error(f"Exception in get_peer_name: {e}")
        return None

def handle_error(message):
    """
    Print an error message.
    
    Parameters:
        message: The error message to display
    """
    print(f"Error: {message}")

def socket_ntohs(netshort):
    """
    Convert a 16-bit integer from network byte order to host byte order.
    
    Network byte order is always big-endian (most significant byte first).
    Host byte order depends on your computer (big-endian or little-endian).
    
    Parameters:
        netshort: 16-bit integer in network byte order
        
    Returns:
        16-bit integer in host byte order
    """
    return ws2_32.ntohs(netshort)

def close_socket(sock, cleanup=False):
    """
    Close a socket and optionally clean up Winsock.
    
    Parameters:
        sock: Socket handle to close
        cleanup: If True, also call WSACleanup to release Winsock resources
    """
    # Close the socket
    ws2_32.closesocket(sock)
    
    # If requested, clean up Winsock resources
    if cleanup:
        ws2_32.WSACleanup()

# ---------------------- SOCKET OPTION FUNCTIONS ----------------------

def set_tcp_option(sock, option_name, option_value):
    """
    Set a TCP-specific socket option.
    
    Parameters:
        sock: Socket handle
        option_name: TCP option identifier (e.g., TCP_NODELAY)
        option_value: Value to set the option to
        
    Returns:
        True if successful, False otherwise
    """
    # If the value is a boolean, convert to integer (1 for True, 0 for False)
    if isinstance(option_value, bool):
        option_value = 1 if option_value else 0
    
    # Create a C integer to hold the option value
    value = ctypes.c_int(option_value)
    
    # Set the socket option
    result = ws2_32.setsockopt(sock, IPPROTO_TCP, option_name, 
                              ctypes.byref(value), ctypes.sizeof(value))
    
    # Check if operation succeeded
    if result != 0:
        error = ws2_32.WSAGetLastError()
        handle_error(f"Failed to set TCP option {option_name}, error: {error}")
        return False
    return True

def set_ip_option(sock, option_name, option_value):
    """
    Set an IP-specific socket option.
    
    Parameters:
        sock: Socket handle
        option_name: IP option identifier (e.g., IP_TTL)
        option_value: Value to set the option to
        
    Returns:
        True if successful, False otherwise
    """
    # Create a C integer to hold the option value
    value = ctypes.c_int(option_value)
    
    # Set the socket option at IP protocol level
    result = ws2_32.setsockopt(sock, IPPROTO_IP, option_name, 
                              ctypes.byref(value), ctypes.sizeof(value))
    
    # Check if operation succeeded
    if result != 0:
        error = ws2_32.WSAGetLastError()
        handle_error(f"Failed to set IP option {option_name}, error: {error}")
        return False
    return True

def set_socket_option(sock, option_name, option_value):
    """
    Set a general socket option.
    
    Parameters:
        sock: Socket handle
        option_name: Socket option identifier (e.g., SO_REUSEADDR)
        option_value: Value to set the option to
        
    Returns:
        True if successful, False otherwise
    """
    # Special handling for the SO_LINGER option, which takes a structure
    if option_name == SO_LINGER:
        if isinstance(option_value, tuple):
            # Create a linger structure from the tuple (on_off, linger_time)
            linger = LingerStruct()
            linger.l_onoff = option_value[0]   # Enable (1) or disable (0)
            linger.l_linger = option_value[1]  # Linger time in seconds
            
            # Set the option with the linger structure
            result = ws2_32.setsockopt(sock, SOL_SOCKET, option_name,
                                      ctypes.byref(linger), ctypes.sizeof(linger))
        else:
            # If not a tuple, we can't set the option
            handle_error("SO_LINGER requires a tuple of (on_off, linger_time)")
            return False
    else:
        # For most options, we just pass an integer value
        value = ctypes.c_int(option_value)
        result = ws2_32.setsockopt(sock, SOL_SOCKET, option_name,
                                  ctypes.byref(value), ctypes.sizeof(value))
    
    # Check if operation succeeded
    if result != 0:
        error = ws2_32.WSAGetLastError()
        handle_error(f"Failed to set socket option {option_name}, error: {error}")
        return False
    return True

def configure_tcp_keepalive(sock, enable=True, idle_time=120, interval=10, count=8):
    """
    Configure TCP keepalive parameters using Windows-specific method.
    
    Keepalives are special packets sent to maintain a connection when no data is being sent.
    This is useful for detecting if the other end has disconnected.
    
    Parameters:
        sock: Socket handle
        enable: Whether to enable keepalive
        idle_time: Seconds before first keepalive is sent
        interval: Seconds between keepalives
        count: Number of keepalives before giving up (not directly supported on Windows)
        
    Returns:
        True if successful, False otherwise
    """
    # First enable keepalive at the socket level
    if not set_socket_option(sock, SO_KEEPALIVE, enable):
        return False
    
    if enable:
        # Windows uses a special IOCTL call to configure keepalive parameters
        # Create a structure with the desired values
        ka_vals = KeepaliveVals()
        ka_vals.onoff = 1                           # Enable keepalive
        ka_vals.keepalivetime = idle_time * 1000    # Convert seconds to milliseconds
        ka_vals.keepaliveinterval = interval * 1000 # Convert seconds to milliseconds
        
        # Cast the structure to a byte pointer as required by WSAIoctl
        in_buffer = ctypes.cast(ctypes.byref(ka_vals), ctypes.POINTER(ctypes.c_ubyte))
        bytes_returned = ctypes.c_ulong(0)
        
        try:
            # Set the keepalive values using WSAIoctl
            result = ws2_32.WSAIoctl(
                sock,                # Socket handle
                SIO_KEEPALIVE_VALS,  # Control code for keepalive
                in_buffer,           # Input buffer with keepalive values
                ctypes.sizeof(ka_vals),  # Size of input buffer
                None,                # No output buffer needed
                0,                   # Output buffer size
                ctypes.byref(bytes_returned),  # Bytes returned
                None,                # No overlapped operation
                None                 # No completion routine
            )
            
            # Check if operation succeeded
            if result != 0:
                error = ws2_32.WSAGetLastError()
                handle_error(f"Failed to configure keepalive values, error: {error}")
                return False
                
        except Exception as e:
            handle_error(f"Exception configuring keepalive: {e}")
            return False
    
    return True

def set_tcp_nodelay(sock, enable=True):
    """
    Enable or disable the Nagle algorithm for TCP sockets.
    
    The Nagle algorithm reduces network traffic by buffering small packets.
    Disabling it (TCP_NODELAY=True) improves responsiveness but increases
    network traffic.
    
    Parameters:
        sock: Socket handle
        enable: True to disable Nagle's algorithm, False to enable it
        
    Returns:
        True if successful, False otherwise
    """
    return set_tcp_option(sock, TCP_NODELAY, enable)

def set_buffer_sizes(sock, receive_size=8192, send_size=8192):
    """
    Set socket receive and send buffer sizes.
    
    Larger buffers can improve throughput, especially on high-latency connections.
    
    Parameters:
        sock: Socket handle
        receive_size: Size of the receive buffer in bytes
        send_size: Size of the send buffer in bytes
        
    Returns:
        True if both operations succeeded, False otherwise
    """
    # Set receive buffer size
    recv_ok = set_socket_option(sock, SO_RCVBUF, receive_size)
    
    # Set send buffer size
    send_ok = set_socket_option(sock, SO_SNDBUF, send_size)
    
    # Return True only if both operations succeeded
    return recv_ok and send_ok

# ---------------------- HIGHER-LEVEL FUNCTIONS ----------------------

def create_tcp_socket_with_options(nodelay=True, reuse_addr=True, 
                                 keepalive=False, recv_buffer=8192, 
                                 send_buffer=8192):
    """
    Create a TCP socket with common options configured.
    
    This is a convenience function that creates a socket and sets
    the most commonly used options in one call.
    
    Parameters:
        nodelay: Whether to disable Nagle's algorithm
        reuse_addr: Whether to allow reusing local addresses
        keepalive: Whether to enable keepalive packets
        recv_buffer: Size of the receive buffer in bytes
        send_buffer: Size of the send buffer in bytes
        
    Returns:
        Socket handle if successful, None otherwise
    """
    # Create the socket
    sock = create_tcp_socket()
    if sock is None:
        return None
        
    # Set Nagle's algorithm (TCP_NODELAY)
    if nodelay:
        set_tcp_nodelay(sock, True)
        
    # Set address reuse
    if reuse_addr:
        set_socket_option(sock, SO_REUSEADDR, 1)
        
    # Set buffer sizes
    set_buffer_sizes(sock, recv_buffer, send_buffer)
    
    # Configure keepalive if requested
    if keepalive:
        configure_tcp_keepalive(sock, True)
    
    return sock

def perform_tcp_handshake(sock, ip, port, syn_retry=3, timeout_sec=10):
    """
    Perform TCP handshake with more control over the connection parameters.
    
    Parameters:
        sock: Socket handle
        ip: Server IP address
        port: Server port
        syn_retry: Number of SYN packet retries
        timeout_sec: Connection timeout in seconds
        
    Returns:
        True if connection succeeded, False otherwise
    """
    # Set connection timeout
    timeout_ms = timeout_sec * 1000
    try:
        # Windows-specific timeout setting using SO_SNDTIMEO
        # We pack the timeout as seconds and microseconds (struct timeval format)
        tv = struct.pack('ll', timeout_sec, 0)
        ws2_32.setsockopt(sock, SOL_SOCKET, 0x7002, tv, len(tv))  # 0x7002 is SO_SNDTIMEO
    except Exception as e:
        print(f"Warning: Could not set connection timeout: {e}")
    
    # Perform the actual connection (handshake)
    return connect_to_server(sock, ip, port)

# ---------------------- SERVER AND CLIENT THREADS ----------------------

def server_thread():
    """
    Server thread function that sets up a socket server and handles one client.
    
    This function:
    1. Creates a server socket with custom options
    2. Binds to a local address
    3. Listens for connections
    4. Accepts one client connection
    5. Exchanges data with the client
    6. Closes all connections
    """
    print("[Server] Starting server with custom TCP options...")
    
    # Create server socket with larger buffers for performance
    server_sock = create_tcp_socket_with_options(
        nodelay=True,       # Disable Nagle's algorithm for better responsiveness
        reuse_addr=True,    # Allow reusing the address if needed
        keepalive=True,     # Enable keepalive to detect disconnected clients
        recv_buffer=16384,  # 16KB receive buffer
        send_buffer=16384   # 16KB send buffer
    )
    
    # Check if socket creation succeeded
    if server_sock is None:
        print("[Server] Failed to create socket")
        return
        
    # Configure additional socket options
    
    # Set linger option: when socket is closed, wait up to 5 seconds to send pending data
    set_socket_option(server_sock, SO_LINGER, (1, 5))
    
    # Set Time-To-Live (TTL) to 64 hops
    set_ip_option(server_sock, IP_TTL, 64)
    
    # Bind the socket to the loopback address and port 5090
    if not bind_socket(server_sock, "127.0.0.1", 5090):
        print("[Server] Failed to bind socket")
        return
        
    # Start listening for connections with a queue of 5
    if not listen_for_connections(server_sock, 5):
        print("[Server] Failed to listen on socket")
        return
        
    print("[Server] Listening on 127.0.0.1:5090")
    
    # Accept a client connection
    client_data = accept_connection(server_sock)
    if not client_data:
        print("[Server] Failed to accept connection")
        return
        
    # Unpack the client socket and address information
    client_sock, client_addr = client_data
    print(f"[Server] Client connected from {client_addr}!")
    
    # Configure the client socket for optimal communication
    try:
        # Disable Nagle's algorithm for better responsiveness
        set_tcp_nodelay(client_sock, True)
        
        # Configure keepalive to detect if the client disconnects
        # - idle_time=30: Wait 30 seconds before sending first keepalive
        # - interval=5: Send a keepalive every 5 seconds if no response
        # - count=3: Try 3 times before considering the connection dead
        configure_tcp_keepalive(client_sock, idle_time=30, interval=5, count=3)
    except Exception as e:
        print(f"[Server] Error setting socket options: {e}")
    
    # Exchange data with the client (3 rounds)
    for i in range(3):
        # Receive message from client
        data = receive_data(client_sock)
        print(f"[Server] Received: {data}")
        
        # Send response to client
        response = f"Server response #{i+1}"
        send_data(client_sock, response)
        print(f"[Server] Sent: {response}")
        
    # Clean up: close client and server sockets
    close_socket(client_sock)
    close_socket(server_sock, cleanup=True)  # Also clean up Winsock
    print("[Server] Closed connections")

def client_thread():
    """
    Client thread function that connects to a server and exchanges data.
    
    This function:
    1. Waits for the server to start
    2. Creates a client socket with custom options
    3. Connects to the server
    4. Exchanges data with the server
    5. Closes the connection
    """
    # Wait for server to start
    time.sleep(1)
    
    print("[Client] Starting client with custom TCP options...")
    
    # Create client socket with options
    client_sock = create_tcp_socket_with_options(
        nodelay=True,      # Disable Nagle's algorithm for better responsiveness
        reuse_addr=False,  # Don't need to reuse address for client
        keepalive=True,    # Enable keepalive to detect server disconnection
        recv_buffer=8192,  # 8KB receive buffer
        send_buffer=8192   # 8KB send buffer
    )
    
    # Check if socket creation succeeded
    if client_sock is None:
        print("[Client] Failed to create socket")
        return
        
    # Connect to the server with custom parameters
    print("[Client] Connecting to server...")
    if not perform_tcp_handshake(client_sock, "127.0.0.1", 5090, 
                               syn_retry=3, timeout_sec=5):
        print("[Client] Failed to connect to server")
        return
        
    print("[Client] Connected to server!")
    
    # Exchange data with the server (3 rounds)
    for i in range(3):
        # Send message to server
        message = f"Client message #{i+1}"
        send_data(client_sock, message)
        print(f"[Client] Sent: {message}")
        
        # Receive response from server
        response = receive_data(client_sock)
        print(f"[Client] Received: {response}")
        
    # Clean up: close client socket
    close_socket(client_sock)
    print("[Client] Closed connection")

# ---------------------- MAIN PROGRAM ----------------------

if __name__ == "__main__":
    # This code runs when the script is executed directly
    
    # Create and start the server thread
    # Using daemon=True means the thread will exit when the main program exits
    server = threading.Thread(target=server_thread)
    server.daemon = True
    server.start()
    
    # Create and start the client thread
    client = threading.Thread(target=client_thread)
    client.daemon = True
    client.start()
    
    # Wait for both threads to complete
    # This ensures the main program doesn't exit until both threads are done
    server.join()
    client.join()
    
    print("Example completed")