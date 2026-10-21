# CanteenCenter
# Canteen Menu System

A web-based Canteen Menu System designed to make it easier for students to view available food items and for canteen staff to manage menus, orders, students, and reports.

## 📌 About the Project

The Canteen Menu System is a simple web application developed to digitize basic canteen operations. Instead of depending completely on a physical menu or manual records, the system provides a centralized platform for managing food items, student information, orders, and reports.

The project focuses on providing a simple and user-friendly experience while keeping the canteen management process organized.

## ✨ Features

- View available food items and menu
- Add and manage food items
- Manage student information
- Manage orders
- View order details
- Generate and view reports
- Simple and user-friendly interface
- SQLite database for storing application data

## 🛠️ Technologies Used

- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript

## 📂 Project Structure

canteen-center/
│
├── app.py
├── schema.sql
├── requirements.txt
│
├── templates/
│   ├── orders.html
│   ├── pos.html
│   ├── reports.html
│   └── students.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
└── README.md


pip install flask
python app.py

Open http://127.0.0.1:5000. Delete canteen.db to reset the sample data.
