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
logging.debug(f"client_secret_path ----- {client_secret_path}")

# Define the running flag globally
running = True

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# Function to handle form submission
async def execute_script():
    media_name = media_var.get()
    start_date = cal_start.get()
    end_date = cal_end.get()
    ##

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


async def stop_main():
    global running
    running = False


def on_button_click():
    # Create and run the async task
    task = asyncio.create_task(execute_script())
    task.add_done_callback(lambda t: asyncio.create_task(stop_main()))


# Create main window
root = tk.Tk()
root.title("Media Script Runner")

# Create dropdown for media name
media_var = tk.StringVar()
media_label = tk.Label(root, text="Select Media Name")
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
    "Woman'sHealth"
]  # Add your media options here
media_dropdown = ttk.OptionMenu(root, media_var, media_options[0], *media_options)
media_dropdown.grid(row=0, column=1, padx=10, pady=10)

# Create date pickers for start and end date
start_label = tk.Label(root, text="Select Start Date")
start_label.grid(row=1, column=0, padx=10, pady=10)
cal_start = DateEntry(
    root,
    width=12,
    background="darkblue",
    foreground="white",
    borderwidth=2,
    date_pattern="yyyy-mm-dd",
)
cal_start.grid(row=1, column=1, padx=10, pady=10)

end_label = tk.Label(root, text="Select End Date")
end_label.grid(row=2, column=0, padx=10, pady=10)
cal_end = DateEntry(
    root,
    width=12,
    background="darkblue",
    foreground="white",
    borderwidth=2,
    date_pattern="yyyy-mm-dd",
)
cal_end.grid(row=2, column=1, padx=10, pady=10)


# Create execute button
execute_button = tk.Button(root, text="Execute", command=on_button_click)
execute_button.grid(row=3, columnspan=2, pady=20)


async def main():
    global running
    while running:
        root.update()  # Run Tkinter events
        await asyncio.sleep(0.01)  # Small sleep to keep the loop running smoothly


asyncio.run(main())
# Start the GUI loop
# root.mainloop()
