import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import threading
import time
from PIL import Image, ImageTk  # For handling the splash image
import os

# Define the product catalog with prices
product_catalog = [
    {"name": "Apple", "price": 00.00},
    {"name": "Banana", "price": 00.00},
    {"name": "Orange", "price": 00.00},
    {"name": "Water", "price": 00.00},
    {"name": "Soda", "price": 00.00},
    {"name": "Chips", "price": 00.00},
    {"name": "KitKat", "price": 25.00},
    {"name": "goodday", "price": 25.00},
    {"name": "HidenSeek", "price": 30.00},
    {"name": "Unibic", "price": 30.00},
]

class SplashScreen:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)  # Remove window decorations for splash screen
        self.root.geometry("800x600")  # Set a size for the splash screen
        self.root.configure(bg="#f0f0f0")
        
        # Center the window on the screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - 800) // 2
        y = (screen_height - 600) // 2
        self.root.geometry(f"800x600+{x}+{y}")
        
        try:
            # Load the splash image
            script_dir = os.path.dirname(os.path.abspath(__file__))
            img_path = os.path.join(script_dir, "init.jpg")
            
            # Check if the file exists
            if not os.path.exists(img_path):
                raise FileNotFoundError(f"Splash image not found at {img_path}")
                
            # Open the original image
            img = Image.open(img_path)
            
            # Calculate the aspect ratio
            original_width, original_height = img.size
            aspect_ratio = original_width / original_height
            
            # Set splash window size maintaining aspect ratio
            window_width = 800
            window_height = int(window_width / aspect_ratio)
            
            # Update the window size
            self.root.geometry(f"{window_width}x{window_height}")
            
            # Resize the image to fit the splash window while maintaining aspect ratio
            img = img.resize((window_width, window_height), Image.LANCZOS)
            self.splash_img = ImageTk.PhotoImage(img)
            
            # Create a label with the image
            splash_label = tk.Label(self.root, image=self.splash_img)
            splash_label.pack(fill=tk.BOTH, expand=True)
            
            # Update the window to show the splash image
            self.root.update()
            
            # Schedule the transition to main application after 4 seconds
            self.root.after(4000, self.close_splash)
            
        except Exception as e:
            # If there's an error loading the splash image, log it and proceed to main app
            print(f"Error loading splash screen: {str(e)}")
            self.root.after(100, self.close_splash)
    
    def close_splash(self):
        """Close the splash screen and initialize the main application"""
        # Hide the splash screen
        self.root.withdraw()
        
        # Restore normal window behavior
        self.root.overrideredirect(False)
        
        # Create a new toplevel window for the main application
        main_window = tk.Toplevel(self.root)
        main_window.title("Smart Retail Verification System | Edge_AI_CP_330 | Tanisha Bhatia | Shubham Lanjewar | Prof. Pandarasamy Arjunan")
        main_window.geometry("1000x700")  # Slightly larger to accommodate prices
        
        # Make this window behave like a main window
        main_window.protocol("WM_DELETE_WINDOW", self.root.destroy)
        
        # Create and show the main application window
        app = RetailVerificationSystem(main_window)
        
        # Show the main window and hide the root window
        main_window.deiconify()
        self.root.withdraw()
        
        # Keep a reference to the main window and app to prevent garbage collection
        self.main_window = main_window
        self.app = app


class RetailVerificationSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Retail Verification System | Edge_AI_CP_330 | Tanisha Bhatia | Shubham Lanjewar | Prof. Pandarasamy Arjunan")
        self.root.geometry("1000x700")  # Increased to accommodate prices
        self.root.configure(bg="#f0f0f0")
        
        # Create a main canvas with scrollbar
        self.main_canvas = tk.Canvas(self.root, bg="#f0f0f0")
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        
        # Place canvas and scrollbar in root window using grid
        self.main_canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Configure the canvas to work with the scrollbar
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Create a frame inside the canvas to hold all widgets
        self.content_frame = ttk.Frame(self.main_canvas)
        
        # Add the content frame to the canvas
        self.canvas_frame = self.main_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        
        # Configure root window grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Serial connection variables
        self.serial_port = None
        self.is_connected = False
        self.detected_items = []
        
        # Raw data buffer for debugging
        self.raw_data_buffer = []
        
        # Create a dictionary of product names -> prices for easy lookup
        self.product_prices = {product["name"]: product["price"] for product in product_catalog}
        
        # Create GUI components
        self.create_widgets()
        
        # Start a thread to listen for serial data
        self.should_stop = False
        self.serial_thread = None
        
        # Automatically find available ports
        self.refresh_ports()
        
        # Bind events for scrolling
        self.content_frame.bind("<Configure>", self.on_frame_configure)
        self.main_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Bind mousewheel for scrolling
        self.main_canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        
        # Update idletasks to ensure content_frame has the correct size
        self.content_frame.update_idletasks()
        
        # Update the scrollable region
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        
        # Calculate the initial total (which should be 0)
        self.calculate_total()
    
    def on_frame_configure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        """When canvas is resized, update the window size"""
        # Update the width of the content frame to match the canvas
        canvas_width = event.width
        self.main_canvas.itemconfig(self.canvas_frame, width=canvas_width)
    
    def on_mousewheel(self, event):
        """Handle mousewheel scrolling"""
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.content_frame, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Connection frame
        connection_frame = ttk.LabelFrame(main_frame, text="Device Connection", padding=10)
        connection_frame.pack(fill=tk.X, pady=10)
        
        # Port selection
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(connection_frame, textvariable=self.port_var, width=20)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.refresh_button = ttk.Button(connection_frame, text="Refresh", command=self.refresh_ports)
        self.refresh_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.connect_button = ttk.Button(connection_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Baud rate selection
        ttk.Label(connection_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.baud_var = tk.StringVar(value="115200")
        baud_rates = ["9600", "19200", "38400", "57600", "115200", "230400"]
        self.baud_combo = ttk.Combobox(connection_frame, textvariable=self.baud_var, values=baud_rates, width=20)
        self.baud_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Status indicator
        self.status_label = ttk.Label(connection_frame, text="Status: Disconnected", foreground="red")
        self.status_label.grid(row=0, column=4, padx=5, pady=5, rowspan=2)
        
        # Manual entry frame
        manual_frame = ttk.LabelFrame(main_frame, text="Biller Item Entry", padding=10)
        manual_frame.pack(fill=tk.X, pady=10)
        
        # Item entry - REPLACED text entry with combobox
        ttk.Label(manual_frame, text="Item:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        # Create item combobox with product catalog names
        product_names = [product["name"] for product in product_catalog]
        self.item_var = tk.StringVar()
        self.item_combo = ttk.Combobox(manual_frame, textvariable=self.item_var, values=product_names, width=20)
        self.item_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # When an item is selected, show its price
        self.item_combo.bind("<<ComboboxSelected>>", self.display_selected_price)
        
        # Price display
        ttk.Label(manual_frame, text="Price (₹):").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.price_var = tk.StringVar(value="0.00")
        price_display = ttk.Label(manual_frame, textvariable=self.price_var)
        price_display.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Quantity entry
        ttk.Label(manual_frame, text="Quantity:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.quantity_entry = ttk.Spinbox(manual_frame, from_=1, to=100, width=5)
        self.quantity_entry.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, "1")
        
        # Add item button
        self.add_button = ttk.Button(manual_frame, text="Add Item", command=self.add_item)
        self.add_button.grid(row=0, column=6, padx=5, pady=5)
        
        # Display frames
        display_frame = ttk.Frame(main_frame)
        display_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Biller items frame
        biller_frame = ttk.LabelFrame(display_frame, text="Biller Items", padding=10)
        biller_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Biller items treeview - added Price and Total columns
        self.biller_tree = ttk.Treeview(biller_frame, columns=("Item", "Price", "Quantity", "Total"), show="headings", height=6)
        self.biller_tree.heading("Item", text="Item")
        self.biller_tree.heading("Price", text="Price (₹)")
        self.biller_tree.heading("Quantity", text="Qty")
        self.biller_tree.heading("Total", text="Total (₹)")
        self.biller_tree.column("Item", width=150)
        self.biller_tree.column("Price", width=70)
        self.biller_tree.column("Quantity", width=50)
        self.biller_tree.column("Total", width=80)
        self.biller_tree.pack(fill=tk.BOTH, expand=True)
        
        biller_scrollbar = ttk.Scrollbar(biller_frame, orient="vertical", command=self.biller_tree.yview)
        biller_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.biller_tree.configure(yscrollcommand=biller_scrollbar.set)
        
        # Total price frame below the biller items
        total_frame = ttk.Frame(biller_frame)
        total_frame.pack(fill=tk.X, pady=5)
        
        # Total price label
        ttk.Label(total_frame, text="TOTAL:", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=5)
        self.total_price_var = tk.StringVar(value="₹0.00")
        ttk.Label(total_frame, textvariable=self.total_price_var, font=("Arial", 12, "bold")).pack(side=tk.RIGHT, padx=5)
        
        # Detected items frame
        detected_frame = ttk.LabelFrame(display_frame, text="Detected Items", padding=10)
        detected_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Detected items treeview - added Price column
        self.detected_tree = ttk.Treeview(detected_frame, columns=("Item", "Count", "Price", "Confidence"), show="headings", height=6)
        self.detected_tree.heading("Item", text="Item")
        self.detected_tree.heading("Count", text="Count")
        self.detected_tree.heading("Price", text="Price (₹)")
        self.detected_tree.heading("Confidence", text="Confidence")
        self.detected_tree.column("Item", width=150)
        self.detected_tree.column("Count", width=50)
        self.detected_tree.column("Price", width=70)
        self.detected_tree.column("Confidence", width=100)
        self.detected_tree.pack(fill=tk.BOTH, expand=True)
        
        detected_scrollbar = ttk.Scrollbar(detected_frame, orient="vertical", command=self.detected_tree.yview)
        detected_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.detected_tree.configure(yscrollcommand=detected_scrollbar.set)
        
        # Control buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Clear button
        self.clear_button = ttk.Button(button_frame, text="Clear All", command=self.clear_all)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Command buttons frame for Nicla Vision controls
        command_frame = ttk.Frame(button_frame)
        command_frame.pack(side=tk.LEFT, padx=20)
        
        # Start/Stop/Status buttons
        self.start_button = ttk.Button(command_frame, text="Start Detection", command=lambda: self.send_command("start"))
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(command_frame, text="Stop Detection", command=lambda: self.send_command("stop"))
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.status_button = ttk.Button(command_frame, text="Get Status", command=lambda: self.send_command("status"))
        self.status_button.pack(side=tk.LEFT, padx=5)
        
        # Test Connection button
        self.test_button = ttk.Button(command_frame, text="Test Connection", command=self.test_connection)
        self.test_button.pack(side=tk.LEFT, padx=5)
        
        # DEBUG: Force update button to manually trigger detection update
        self.force_update_button = ttk.Button(command_frame, text="DEBUG: Force Update", command=self.force_update)
        self.force_update_button.pack(side=tk.LEFT, padx=5)
        
        # VERY PROMINENT Verify button - moved above Raw Data section
        verify_frame = ttk.Frame(main_frame)
        verify_frame.pack(fill=tk.X, pady=10)
        
        self.verify_button = tk.Button(
            verify_frame, 
            text="VERIFY ITEMS", 
            command=self.verify_items,
            bg="green",
            fg="white",
            font=("Arial", 14, "bold"),
            height=2,
            width=20
        )
        self.verify_button.pack(side=tk.TOP, pady=10)
        
        # Raw data display frame - now below the VERIFY ITEMS button
        raw_data_frame = ttk.LabelFrame(main_frame, text="Raw Data from Nicla Vision", padding=10)
        raw_data_frame.pack(fill=tk.X, pady=10)
        
        # Raw data text area
        self.raw_data_text = scrolledtext.ScrolledText(raw_data_frame, height=5, width=80, wrap=tk.WORD)
        self.raw_data_text.pack(fill=tk.BOTH, expand=True)
        
        # Debug output frame
        debug_frame = ttk.LabelFrame(main_frame, text="Debug Output", padding=10)
        debug_frame.pack(fill=tk.X, pady=10)
        
        # Debug text
        self.debug_text = scrolledtext.ScrolledText(debug_frame, height=5, width=80, wrap=tk.WORD)
        self.debug_text.pack(fill=tk.BOTH, expand=True)
        
        # Status message
        self.message_var = tk.StringVar()
        self.message_var.set("Ready for verification")
        self.message_label = ttk.Label(main_frame, textvariable=self.message_var, font=("Arial", 12), foreground="blue")
        self.message_label.pack(fill=tk.X, pady=5)
    
    def display_selected_price(self, event=None):
        """Update the price display when an item is selected"""
        selected_item = self.item_var.get()
        if selected_item in self.product_prices:
            price = self.product_prices[selected_item]
            self.price_var.set(f"{price:.2f}")
        else:
            self.price_var.set("0.00")
    
    def calculate_total(self):
        """Calculate the total price of all items in the biller tree"""
        total = 0.0
        for item_id in self.biller_tree.get_children():
            values = self.biller_tree.item(item_id, 'values')
            if len(values) >= 4:  # Make sure we have enough values (including total)
                try:
                    item_total = float(values[3])  # Total column
                    total += item_total
                except (ValueError, TypeError):
                    self.log_debug(f"Error calculating total for item: {values}")
        
        # Update the total price display
        self.total_price_var.set(f"₹{total:.2f}")
        self.log_debug(f"Total price updated: ₹{total:.2f}")
    
    def force_update(self):
        """Debug function to manually trigger an update with test data"""
        self.log_debug("Forcing update with test data")
        test_detections = [
            {"class": "Apple", "quantity": 2, "score": 0.95},
            {"class": "KitKat", "quantity": 1, "score": 0.85},
            {"class": "Chips", "quantity": 3, "score": 0.75}
        ]
        self.process_detections(test_detections)
    
    def test_connection(self):
        """Test the connection with a simple command"""
        if not self.is_connected or not self.serial_port:
            messagebox.showwarning("Connection Required", "Please connect to the Nicla Vision device first")
            return
        
        try:
            # Send a newline character to trigger a response
            self.serial_port.write(b'\r\n')
            self.log_debug("Sent test newline character")
            self.log_raw_data('\r\n', is_incoming=False)
        except Exception as e:
            self.log_debug(f"Error sending test: {str(e)}")
    
    def refresh_ports(self):
        """Find all available serial ports"""
        available_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = available_ports
        
        if available_ports:
            self.port_var.set(available_ports[0])
            self.log_debug(f"Found ports: {available_ports}")
        else:
            self.port_var.set("")
            self.log_debug("No serial ports found! Check your device connection.")
    
    def log_debug(self, message):
        """Add a message to the debug output"""
        timestamp = time.strftime("%H:%M:%S")
        self.debug_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.debug_text.see(tk.END)
        print(message)  # Also print to console
    
    def log_raw_data(self, data, is_incoming=True):
        """Add raw data to the raw data display"""
        timestamp = time.strftime("%H:%M:%S")
        direction = "<<" if is_incoming else ">>"
        
        # Make sure we have a string
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='replace')
            
        entry = f"[{timestamp}] {direction} {data}"
        
        # Update display
        self.raw_data_text.insert(tk.END, entry + "\n")
        self.raw_data_text.see(tk.END)
        
        # Also print to console for debugging
        print(f"RAW: {entry}")
    
    def toggle_connection(self):
        if not self.is_connected:
            self.connect_device()
        else:
            self.disconnect_device()
    
    def connect_device(self):
        try:
            port = self.port_var.get()
            baud_rate = int(self.baud_var.get())
            
            if not port:
                self.log_debug("Error: No port selected!")
                messagebox.showerror("Connection Error", "No port selected")
                return
            
            self.log_debug(f"Attempting to connect to {port} at {baud_rate} baud...")
            
            # Try to open the serial port
            self.serial_port = serial.Serial(port, baud_rate, timeout=1)
            self.is_connected = True
            self.status_label.config(text="Status: Connected", foreground="green")
            self.connect_button.config(text="Disconnect")
            
            self.log_debug(f"Successfully connected to {port}")
            self.message_var.set(f"Connected to {port}")
            
            # Clear the raw data display
            self.raw_data_text.delete(1.0, tk.END)
            
            # Start the serial thread
            self.should_stop = False
            self.serial_thread = threading.Thread(target=self.read_serial_data)
            self.serial_thread.daemon = True
            self.serial_thread.start()
            
            # Send a status command to test the connection
            self.root.after(500, lambda: self.send_command("status"))
            
        except Exception as e:
            self.log_debug(f"Connection error: {str(e)}")
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
    
    def disconnect_device(self):
        if self.serial_port:
            # Stop the serial thread
            self.should_stop = True
            if self.serial_thread:
                self.serial_thread.join(timeout=1.0)
            
            self.serial_port.close()
            self.serial_port = None
            self.log_debug("Disconnected from device")
        
        self.is_connected = False
        self.status_label.config(text="Status: Disconnected", foreground="red")
        self.connect_button.config(text="Connect")
        self.message_var.set("Device disconnected")
    
    def send_command(self, command):
        """Send a command to the Nicla Vision"""
        if not self.is_connected or not self.serial_port:
            messagebox.showwarning("Connection Required", "Please connect to the Nicla Vision device first")
            return
        
        try:
            cmd_with_newline = f"{command}\r\n"
            self.serial_port.write(cmd_with_newline.encode('utf-8'))
            self.log_debug(f"Sent command: {command}")
            self.log_raw_data(cmd_with_newline, is_incoming=False)
        except Exception as e:
            self.log_debug(f"Error sending command: {str(e)}")
    
    def read_serial_data(self):
        """Thread function to read serial data from Nicla Vision"""
        self.log_debug("Serial reading thread started")
        
        while not self.should_stop:
            try:
                if self.serial_port and self.serial_port.is_open and self.serial_port.in_waiting:
                    # Read one line at a time
                    line = self.serial_port.readline()
                    
                    # Log the raw bytes data
                    self.log_raw_data(line, is_incoming=True)
                    
                    # Try to decode and process the line
                    try:
                        decoded_line = line.decode('utf-8', errors='replace').strip()
                        
                        # Check for "No objects detected" message
                        if "No objects detected" in decoded_line:
                            self.log_debug("No objects detected - clearing detected items list")
                            # Clear the detected items list
                            self.detected_items = []
                            # Update the tree view on the main thread
                            self.root.after(10, self._update_detected_tree)
                            continue
                        
                        # DEBUG: Print the exact line we're processing
                        self.log_debug(f"Processing line: '{decoded_line}'")
                        
                        # Check if this is a detection message
                        if "Sent:" in decoded_line and "DETECTION|" in decoded_line:
                            self.log_debug(f"Found detection in: '{decoded_line}'")
                            
                            # Extract the detection part after "Sent: "
                            detection_part = decoded_line.split("Sent:", 1)[1].strip()
                            self.log_debug(f"Detection part: '{detection_part}'")
                            
                            if detection_part.startswith("DETECTION|"):
                                parts = detection_part.split("|")
                                self.log_debug(f"Split parts: {parts}")
                                
                                # Create detections list
                                detections = []
                                for part in parts[1:]:  # Skip the "DETECTION" part
                                    self.log_debug(f"Processing part: '{part}'")
                                    if ":" in part:
                                        try:
                                            # New format: item:quantity:score
                                            if part.count(":") == 2:
                                                item, quantity_str, score_str = part.split(":", 2)
                                                self.log_debug(f"Found item: '{item}', quantity: '{quantity_str}', score: '{score_str}'")
                                                quantity = int(quantity_str)
                                                score = float(score_str)
                                                detections.append({
                                                    "class": item,
                                                    "quantity": quantity,
                                                    "score": score
                                                })
                                            # Handle old format just in case: item:score
                                            else:
                                                item, score_str = part.split(":", 1)
                                                self.log_debug(f"Found item (old format): '{item}', score: '{score_str}'")
                                                score = float(score_str)
                                                detections.append({
                                                    "class": item,
                                                    "quantity": 1,  # Default quantity is 1 for old format
                                                    "score": score
                                                })
                                        except ValueError as ve:
                                            self.log_debug(f"Error parsing part '{part}': {str(ve)}")
                                
                                if detections:
                                    self.log_debug(f"Found {len(detections)} valid detections. Processing...")
                                    self.process_detections(detections)
                                else:
                                    self.log_debug("No valid detections found in the line.")
                                    # Clear detection list when DETECTION message has no items
                                    self.detected_items = []
                                    self.root.after(10, self._update_detected_tree)
                            else:
                                self.log_debug(f"Not a DETECTION message: {detection_part}")
                        else:
                            # Just log other messages
                            if decoded_line.strip():  # Only log non-empty lines
                                self.log_debug(f"Received message: {decoded_line}")
                            
                    except Exception as e:
                        self.log_debug(f"Error processing data: {str(e)}")
                else:
                    # No data available, sleep briefly
                    time.sleep(0.01)
                    
            except Exception as e:
                self.log_debug(f"Serial reading error: {str(e)}")
                time.sleep(0.1)  # Add a small delay before retrying
        
        self.log_debug("Serial reading thread stopped")
    
    def process_detections(self, detections):
        """Process the detection data from Nicla Vision"""
        # Check if the detections list is empty
        if not detections:
            self.log_debug("Empty detections list - clearing detected items")
            self.detected_items = []
            self.root.after(10, self._update_detected_tree)
            return
            
        # Create a dictionary to count occurrences of each class and calculate average confidence
        detection_counts = {}
        confidence_sums = {}
        
        self.log_debug(f"Processing {len(detections)} detections")
        
        for detection in detections:
            class_name = detection.get('class', 'Unknown')
            quantity = detection.get('quantity', 1)  # Get quantity, default to 1 if not present
            confidence = detection.get('score', 0.0)
            
            self.log_debug(f"Processing detection: class={class_name}, quantity={quantity}, confidence={confidence}")
            
            # Add to counts and sum confidence
            if class_name in detection_counts:
                detection_counts[class_name] += quantity  # Add the quantity instead of 1
                confidence_sums[class_name] += confidence
            else:
                detection_counts[class_name] = quantity  # Set the initial count to the quantity
                confidence_sums[class_name] = confidence
        
        # Update the detected items list
        self.detected_items = []
        for class_name, count in detection_counts.items():
            avg_confidence = confidence_sums[class_name] / (count if count > 0 else 1)
            
            # Get the price for this item, default to 0.00 if not found
            price = self.product_prices.get(class_name, 0.00)
            
            self.detected_items.append({
                'item': class_name,
                'count': count,
                'price': price,
                'confidence': avg_confidence
            })
        
        # Debug output
        self.log_debug(f"Detection counts: {detection_counts}")
        self.log_debug(f"Confidence sums: {confidence_sums}")
        self.log_debug(f"Detected items to display: {self.detected_items}")
        
        # Use explicit function to update the detected items treeview
        self.root.after(10, self._update_detected_tree)
    
    def update_detected_tree(self):
        """Schedule an update of the treeview"""
        self.log_debug("Scheduling update of detected tree")
        # Use after to ensure we're on the main thread
        self.root.after(0, self._update_detected_tree)
    
    def _update_detected_tree(self):
        """Internal function to update the detected tree on the main thread"""
        try:
            self.log_debug("Executing tree update with items: " + str(self.detected_items))
            
            # Clear the current items
            for item in self.detected_tree.get_children():
                self.detected_tree.delete(item)
            
            # Add the new items
            item_count = 0
            for item in self.detected_items:
                item_count += 1
                try:
                    # Include price in the detected tree
                    self.detected_tree.insert('', tk.END, values=(
                        item['item'],
                        item['count'],
                        f"{item['price']:.2f}",
                        f"{item['confidence']:.2f}"
                    ))
                    self.log_debug(f"Added item to tree: {item['item']}")
                except Exception as e:
                    self.log_debug(f"Error adding item {item} to tree: {str(e)}")
            
            self.log_debug(f"Updated detected items tree with {item_count} items")
            
            # Force a refresh of the tree
            self.detected_tree.update()
            
        except Exception as e:
            self.log_debug(f"Error updating detected tree: {str(e)}")
    
    def add_item(self):
        """Add item to the biller's list"""
        # Get the selected item from the combobox instead of text entry
        item_name = self.item_var.get().strip()
        quantity = self.quantity_entry.get()
        
        if not item_name:
            messagebox.showwarning("Input Error", "Please select an item from the dropdown")
            return
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter a valid quantity")
            return
        
        # Get the price for this item
        price = self.product_prices.get(item_name, 0.00)
        total = price * quantity
        
        # Add to the treeview with price and total
        self.biller_tree.insert('', tk.END, values=(item_name, f"{price:.2f}", quantity, f"{total:.2f}"))
        
        # Reset the combobox and quantity entry
        self.item_var.set("")  # Clear the combobox selection
        self.price_var.set("0.00")  # Reset price display
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, "1")  # Reset quantity to 1
        
        self.log_debug(f"Added item: {quantity} x {item_name} @ ₹{price:.2f} = ₹{total:.2f}")
        
        # Calculate and update the total price
        self.calculate_total()
    
    def clear_all(self):
        """Clear all entered and detected items"""
        # Clear the biller items
        for item in self.biller_tree.get_children():
            self.biller_tree.delete(item)
        
        # Clear the detected items
        for item in self.detected_tree.get_children():
            self.detected_tree.delete(item)
        
        # Clear the detected items list
        self.detected_items = []
        
        # Reset the combobox selection and price display
        self.item_var.set("")
        self.price_var.set("0.00")
        
        # Reset the total price
        self.total_price_var.set("₹0.00")
        
        self.log_debug("Cleared all items")
    
    def verify_items(self):
        """Verify if biller items match detected items"""
        self.log_debug("Running verification process...")
        
        if not self.is_connected:
            messagebox.showwarning("Connection Required", "Please connect to the Nicla Vision device first")
            return
        
        # Get biller items
        biller_items = {}
        for item_id in self.biller_tree.get_children():
            values = self.biller_tree.item(item_id, 'values')
            item_name = values[0]
            quantity = int(values[2])  # Now quantity is in the third column
            
            if item_name in biller_items:
                biller_items[item_name] += quantity
            else:
                biller_items[item_name] = quantity
        
        # Get detected items
        detected_items = {}
        for item in self.detected_items:
            detected_items[item['item']] = item['count']
        
        self.log_debug(f"Verifying - Billed items: {biller_items}")
        self.log_debug(f"Verifying - Detected items: {detected_items}")
        
        # Check if counts match
        mismatches = []
        for item_name, biller_count in biller_items.items():
            detected_count = detected_items.get(item_name, 0)
            if biller_count != detected_count:
                mismatches.append(f"{item_name}: Billed {biller_count}, Detected {detected_count}")
        
        # Check for items detected but not billed
        for item_name, detected_count in detected_items.items():
            if item_name not in biller_items:
                mismatches.append(f"{item_name}: Billed 0, Detected {detected_count}")
        
        # Show the result
        if not mismatches:
            self.log_debug("Verification successful - all items match")
            self.message_var.set("✓ VERIFICATION SUCCESSFUL: All items match!")
            messagebox.showinfo("Verification Result", "All items have been verified successfully!")
        else:
            self.log_debug(f"Verification failed - {len(mismatches)} mismatches found")
            mismatch_message = "The following items do not match:\n\n" + "\n".join(mismatches)
            self.message_var.set("✗ VERIFICATION FAILED: Mismatches found")
            messagebox.showerror("Verification Failed", mismatch_message)


if __name__ == "__main__":
    root = tk.Tk()
    # Start with the splash screen
    splash = SplashScreen(root)
    root.mainloop()