# Customer Ticket Raise

A support ticket system built for **AAR Technologies**. Customers raise issues with a message, images and videos. The admin team sees every ticket in a dashboard, changes its status and replies in a chat on the ticket.

The same React website can later be wrapped as a mobile app (Android and iOS) with Capacitor.

## Features

**Customers**
- Register and log in
- Raise a ticket with title, description, category and priority
- Attach up to 5 images or videos to a ticket, at creation or later
- See only their own tickets, with a status of Open, In Progress or Resolved
- Chat with the support team on each ticket
- Get in-app notifications when support replies or the status changes

**Admins**
- Dashboard with ticket counts by status
- Search tickets, and filter by status, category and priority
- Open any ticket to see the customer, files and conversation
- Change ticket status, and reply to customers
- Team page to create admins, promote customers and remove admin access
- Get notifications for new tickets and customer messages

**General**
- Light and dark mode, with 5 accent colors (purple, pink, blue, teal, orange)
- Responsive layout that works on phones
- Passwords hashed with bcrypt, and login tokens (JWT) that expire after 1 day

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React (Vite), React Router |
| Backend | Python, Flask, Flask-JWT-Extended, Flask-SQLAlchemy, Flask-CORS |
| Database | MySQL |
| File storage | Local `uploads` folder (development), Cloudinary (production, optional) |

## Project structure

```
customer-ticket-raise/
├── backend/
│   ├── app.py              # app setup and blueprint registration
│   ├── extensions.py       # shared database object
│   ├── models.py           # User, Ticket, Message, Attachment, Notification
│   ├── auth.py             # register, login, current user
│   ├── tickets.py          # create and read tickets
│   ├── messages.py         # chat messages on a ticket
│   ├── uploads.py          # image and video upload, file serving
│   ├── storage.py          # saves files locally or to Cloudinary
│   ├── admin.py            # admin tickets, stats, team management
│   ├── notifications.py    # notification helpers and endpoints
│   ├── permissions.py      # reads the current role from the database
│   ├── requirements.txt
│   └── .env                # your private settings (not committed)
└── frontend/
    ├── src/
    │   ├── api.js          # one helper for every call to the server
    │   ├── AuthContext.jsx # login state
    │   ├── theme.js        # light/dark mode and accent colors
    │   ├── utils.js        # date, file and link helpers
    │   ├── App.jsx         # routes and role protection
    │   ├── main.jsx
    │   ├── index.css       # all styles and themes
    │   ├── components/     # Layout, Icon, AuthShell, NotificationBell, ThemeSwitcher
    │   └── pages/          # Login, Register, customer pages, admin pages
    └── .env                # server address (not committed)
```

## Getting started

### Requirements
- Python 3.10 or newer
- Node.js 18 or newer
- MySQL Server

### 1. Database
Open MySQL Workbench (or the MySQL shell) and run:

```sql
CREATE DATABASE customer_tickets CHARACTER SET utf8mb4;
```

The tables are created automatically when the backend starts.

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create `backend/.env`:

```
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_NAME=customer_tickets
JWT_SECRET_KEY=change-this-to-a-long-random-text
FLASK_DEBUG=1
FRONTEND_URL=http://localhost:5173,http://127.0.0.1:5173
```

Start the server:

```bash
python app.py
```

Check it at <http://127.0.0.1:5000/api/health> and <http://127.0.0.1:5000/api/db-test>.

### 3. Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```
VITE_API_URL=http://127.0.0.1:5000
```

Start the website:

```bash
npm run dev
```

Open <http://localhost:5173>.

### 4. Create the first admin
Everyone who registers is a `customer`. To make the first admin:

1. Register a normal account on the website.
2. Run this in MySQL with your email:

```sql
USE customer_tickets;
UPDATE users SET role = 'admin' WHERE email = 'you@example.com';
```

3. Log out and log in again.

After that, admins can add or remove other admins from the **Team** page.

## Environment variables

**Backend (`backend/.env`)**

| Variable | Required | Description |
|---|---|---|
| `DB_USER` | Yes | MySQL user |
| `DB_PASSWORD` | Yes | MySQL password |
| `DB_HOST` | Yes | MySQL host |
| `DB_NAME` | Yes | Database name |
| `DB_PORT` | No | MySQL port (default `3306`) |
| `JWT_SECRET_KEY` | Yes | Long random text used to sign login tokens |
| `FRONTEND_URL` | No | Website addresses allowed to call the API, comma separated |
| `FLASK_DEBUG` | No | Set to `1` in development only |
| `CLOUDINARY_CLOUD_NAME` | No | Turns on cloud file storage |
| `CLOUDINARY_API_KEY` | No | Cloudinary key |
| `CLOUDINARY_API_SECRET` | No | Cloudinary secret |

**Frontend (`frontend/.env`)**

| Variable | Description |
|---|---|
| `VITE_API_URL` | Address of the Flask server |

## API overview

Most routes need a token: `Authorization: Bearer <token>`.

| Method | Route | Access | Description |
|---|---|---|---|
| POST | `/api/auth/register` | Public | Create a customer account |
| POST | `/api/auth/login` | Public | Log in and get a token |
| GET | `/api/auth/me` | Logged in | Current user |
| GET | `/api/tickets/categories` | Public | Categories and priorities |
| POST | `/api/tickets` | Customer | Raise a ticket |
| GET | `/api/tickets` | Customer | List own tickets |
| GET | `/api/tickets/<id>` | Owner or admin | Ticket with messages and files |
| POST | `/api/tickets/<id>/messages` | Owner or admin | Send a chat message |
| POST | `/api/tickets/<id>/attachments` | Owner or admin | Upload images or videos (field name `files`) |
| GET | `/api/files/<filename>` | Public | Serve a locally stored file |
| GET | `/api/admin/tickets` | Admin | All tickets (filters: `status`, `category`, `priority`, `search`) |
| PATCH | `/api/admin/tickets/<id>/status` | Admin | Change status |
| GET | `/api/admin/stats` | Admin | Ticket counts |
| GET | `/api/admin/users` | Admin | List users (filters: `role`, `search`) |
| POST | `/api/admin/users` | Admin | Create a user or admin |
| PATCH | `/api/admin/users/<id>/role` | Admin | Change a user's role |
| GET | `/api/notifications` | Logged in | Latest notifications and unread count |
| POST | `/api/notifications/<id>/read` | Logged in | Mark one as read |
| POST | `/api/notifications/read-all` | Logged in | Mark all as read |

## Upload rules

| Type | Allowed formats | Max size |
|---|---|---|
| Image | jpg, jpeg, png, gif, webp | 5 MB each |
| Video | mp4, mov, webm, mkv | 50 MB each |

At most 5 files per upload, and 100 MB per request.

## Production notes

- Set a strong, private `JWT_SECRET_KEY`, and leave `FLASK_DEBUG` unset.
- Never commit `.env` files. They are listed in `.gitignore`.
- Use cloud storage (Cloudinary) in production, because most hosts delete local files when they restart.
- Run the backend with a production server such as `gunicorn app:app`, not `python app.py`.
- Build the website with `npm run build` and deploy the `dist` folder.
- Set `VITE_API_URL` to the live backend address, and `FRONTEND_URL` to the live website address.
- If the site uses client-side routing, add a rewrite rule so every path serves `index.html`.

## Roadmap

- Email notifications
- Change-password page
- Instant chat delivery (WebSockets)
- Mobile app with push notifications (Capacitor)
- Deployment to a live server

## License

Built for AAR Technologies. All rights reserved unless stated otherwise.
