import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkcalendar import DateEntry
from datetime import datetime
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
import data_extraction
import logging
import asyncio
import sys
import os


# Define the path to client_secret.json depending on the environment
# if getattr(sys, "frozen", False):
#     # If the app is running as a PyInstaller bundle
#     base_path = sys._MEIPASS
# else:
#     # If running in a regular Python environment
#     base_path = os.path.abspath(".")
base_path = os.path.abspath(".")
root_path = os.path.abspath(os.path.join(base_path, "..", ".."))
client_secret_path = os.path.join(root_path, "client_secret.json")
TOKEN_FILE = "access_token.txt"

# Define the running flag globally
running = True

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def save_token_to_file(token):
    with open(TOKEN_FILE, "w") as file:
        file.write(token)

# Function to load the token from a local file
def load_token_from_file():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as file:
            return file.read().strip()
    return ""  # Return an empty string if the file does no

def clear_frame():
    for widget in frame.winfo_children():
        widget.destroy()


def show_main_menu():
    clear_frame()
    # Task selection UI
    tk.Label(frame, text="Main Menu", font=("Arial", 10)).grid(row=1, column=0)

    # Radio buttons for task selection
    task_var = tk.StringVar(value="insight")  # Default selection
    task_name = ["insight", "follower"]
    index = 1
    for task in task_name:
        index = index + 1
        tk.Radiobutton(
            frame, text=task.capitalize(), variable=task_var, value=task
        ).grid(row=index, column=0)

    # Confirm button
    confirm_button = tk.Button(
        frame, text="Confirm", command=lambda: confirm_task(task_var.get())
    )
    confirm_button.grid(row=4, column=0)


# Function to show the Insight UI
def show_insight_ui():
    clear_frame()
    tk.Label(frame, text="Insight UI", font=("Arial", 16)).grid(row=1, column=0)
    # Create dropdown for media name
    media_var = tk.StringVar()
    media_label = tk.Label(frame, text="Select Media Name")
    media_label.grid(row=0, column=0, padx=10, pady=10)

    media_options = [
        "hodinkee",
        "ELLEJAPAN",
        "ELLEbeauty",
        "ELLEgirl",
        "ELLEDecor",
        "ELLEGoumet",
        "Harper'sBAZAAR",
        "25ans",
        "ModernLiving",
        "Richesse",
        "EsquireJapan",
        "Woman'sHealth",
    ]  # Add your media options here
    media_dropdown = ttk.OptionMenu(frame, media_var, media_options[0], *media_options)
    media_dropdown.grid(row=0, column=1, padx=10, pady=10)

    # Create date pickers for start and end date
    start_label = tk.Label(frame, text="Select Start Date")
    start_label.grid(row=1, column=0, padx=10, pady=10)
    cal_start = DateEntry(
        frame,
        width=12,
        background="darkblue",
        foreground="white",
        borderwidth=2,
        date_pattern="yyyy-mm-dd",
    )
    cal_start.grid(row=1, column=1, padx=10, pady=10)

    end_label = tk.Label(frame, text="Select End Date")
    end_label.grid(row=2, column=0, padx=10, pady=10)
    cal_end = DateEntry(
        frame,
        width=12,
        background="darkblue",
        foreground="white",
        borderwidth=2,
        date_pattern="yyyy-mm-dd",
    )
    cal_end.grid(row=2, column=1, padx=10, pady=10)

    # Create execute button
    execute_button = tk.Button(
        frame,
        text="Execute",
        command=lambda: on_button_click_insight(
            media_var.get(), cal_start.get(), cal_end.get()
        ),
    )
    execute_button.grid(row=3, column=0, pady=20)

    # Back Button
    back_button = tk.Button(frame, text="Back", command=show_main_menu)
    back_button.grid(row=3, column=1)


# Function to show the Follower UI
def show_follower_ui():
    clear_frame()
    tk.Label(frame, text="Follower UI", font=("Arial", 10)).grid(
        row=1, column=0, columnspan=3, pady=10
    )
    # Load the saved token
    saved_token = load_token_from_file()

    # Text input for hashtag name
    tk.Label(frame, text="Enter Hashtag Name:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
    hashtag_var = tk.StringVar()
    hashtag_input = tk.Entry(frame, textvariable=hashtag_var, width=30)
    hashtag_input.grid(row=3, column=0, padx=5, pady=5, sticky="we")
    
     # Text input for access token
    tk.Label(frame, text="Access Token:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
    token_var = tk.StringVar(value=saved_token)  # Set default value to saved token
    token_input = tk.Entry(frame, textvariable=token_var, width=40)
    token_input.grid(row=5, column=0, padx=5, pady=5, sticky="we")

    # Execute Button
    execute_button = tk.Button(
        frame,
        text="Execute",
        command=lambda: on_button_click_follower(hashtag_var.get(),token_var.get()),
    )
    execute_button.grid(row=6, column=0, padx=5, pady=10, sticky="e")

    # Back Button
    back_button = tk.Button(frame, text="Back", command=show_main_menu)
    back_button.grid(row=6, column=1, padx=5, pady=10, sticky="w")


# Function to handle form submission
async def execute_insight(media_name, start_date, end_date):
    if media_name and start_date and end_date:
        # OAuth 2.0 flow to get the credentials
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        # Authenticate using the credentials.json
        creds = flow.run_local_server(port=0)
        # Authorize the client
        client = gspread.authorize(creds)
        # Here you can call your Python function with the selected parameters
        logging.debug(
            f"media_name = {media_name}  start_date = {start_date}  end_date = {end_date}"
        )
        try:
            # convert to DateTime
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
            await data_extraction.execute(client, media_name, start_date, end_date)
            messagebox.showinfo(
                "Success",
                f"Media: {media_name}\nStart Date: {start_date}\nEnd Date: {end_date}",
            )
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
            logging.debug("Invalid date format. Please use YYYY-MM-DD.")
    else:
        messagebox.showerror("Error", "Please fill out all fields.")
        return False
    return True


async def execute_follower(hashtag):
    if hashtag:
        print("execute follower")
        #TODO: 
        # await get_follwer.execute
        # messagebox,showinfo("Success")
        pass
    else:
        messagebox.showerror("Error", "Please input a hashtag.")
        return False
    return True


async def stop_main():
    print('stop')
    global running
    running = False


def on_button_click_insight(media_name, start_date, end_date):
    print(
        f"media name = {media_name}  start date = {start_date}  end date = {end_date}"
    )
    # Create and run the async task
    task = asyncio.create_task(execute_insight(media_name, start_date, end_date))
    task.add_done_callback(lambda t: asyncio.create_task(stop_main()) if t.result() else None)


def on_button_click_follower(hashtag,access_token):
    print(f"hashtag ---- {hashtag}")
    save_token_to_file(access_token)
    task = asyncio.create_task(execute_follower(hashtag))
    task.add_done_callback(lambda t: asyncio.create_task(stop_main()) if t.result() else None)


# Function to handle task confirmation
def confirm_task(selected_task):
    if selected_task == "insight":
        show_insight_ui()
    elif selected_task == "follower":
        show_follower_ui()


# Create main window
root = tk.Tk()
root.title("Media Script Runner")


# Frame for switching UI
frame = tk.Frame(root)
frame.grid(row=0, column=0)

# root.mainloop()


async def main():
    global running
    while running:
        root.update()  # Run Tkinter events
        await asyncio.sleep(0.01)  # Small sleep to keep the loop running smoothly


show_main_menu()

asyncio.run(main())
# Start the GUI loop
# root.mainloop()
