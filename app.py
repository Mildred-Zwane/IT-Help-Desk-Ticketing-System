from flask import Flask, render_template, request, redirect, url_for
from email_validator import validate_email, EmailNotValidError
from database import init_db, get_db_connection

app = Flask(__name__)

init_db()


@app.route("/")
def home():
    return render_template("index.html")



@app.route("/submit-ticket", methods=["GET", "POST"])
def submit_ticket():

    if request.method == "POST":

        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip()
        title = request.form["title"].strip()
        category = request.form["category"].strip()
        description = request.form["description"].strip()

        allowed_categories = ["Hardware", "Software", "Network", "Other"]

        if category not in allowed_categories:
            return "Please select a valid problem category.", 400

        if len(full_name) < 3 or len(full_name) > 50:
            return "Full name must be between 3 and 50 characters.", 400

        try:
            validated_email = validate_email(
                email,
                check_deliverability=False
            )
            email = validated_email.normalized

        except EmailNotValidError:
            return "Please enter a valid email address.", 400

        if len(email) > 100:
            return "Email address is too long.", 400

        if len(title) < 5 or len(title) > 100:
            return "Problem title must be between 5 and 100 characters.", 400

        if len(description) < 10 or len(description) > 500:
            return "Problem description must be between 10 and 500 characters.", 400

        connection = get_db_connection()

        try:
            connection.execute("""
                INSERT INTO tickets (
                    full_name,
                    email,
                    title,
                    category,
                    description
                )
                VALUES (?, ?, ?, ?, ?)
            """, (full_name, email, title, category, description))

            connection.commit()

        finally:
            connection.close()

        return render_template("ticket_success.html")

    return render_template("submit_ticket.html")

@app.route("/update-status/<int:ticket_id>", methods=["POST"])
def update_status(ticket_id):

    new_status = request.form["status"]

    allowed_statuses = ["Open", "In Progress", "Resolved"]

    if new_status not in allowed_statuses:
        return "Please select a valid ticket status.", 400

    connection = get_db_connection()

    try:
        connection.execute(
            "UPDATE tickets SET status = ? WHERE id = ?",
            (new_status, ticket_id)
        )

        connection.commit()

    finally:
        connection.close()

    return redirect(url_for("view_tickets"))

@app.route("/view-tickets")
def view_tickets():

    search_query = request.args.get("search", "")
    status_filter = request.args.get("status", "")
    category_filter = request.args.get("category", "")

    connection = get_db_connection()

    try:
        query = "SELECT * FROM tickets WHERE 1=1"
        parameters = []

        if search_query:
            query += """ AND (
                full_name LIKE ?
                OR title LIKE ?
                OR category LIKE ?
            )"""

            parameters.extend([
                "%" + search_query + "%",
                "%" + search_query + "%",
                "%" + search_query + "%"
            ])

        if status_filter:
            query += " AND status = ?"
            parameters.append(status_filter)

        if category_filter:
            query += " AND category = ?"
            parameters.append(category_filter)

        query += " ORDER BY created_at DESC"

        tickets = connection.execute(
            query, parameters
        ).fetchall()

    finally:
        connection.close()

    return render_template(
        "view_tickets.html",
        tickets=tickets,
        search_query=search_query,
        status_filter=status_filter,
        category_filter=category_filter
    )

@app.route("/dashboard")
def dashboard():

    connection = get_db_connection()

    try:
        total_tickets = connection.execute(
            "SELECT COUNT(*) FROM tickets"
        ).fetchone()[0]

        open_tickets = connection.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'Open'"
        ).fetchone()[0]

        in_progress_tickets = connection.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'In Progress'"
        ).fetchone()[0]

        resolved_tickets = connection.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'Resolved'"
        ).fetchone()[0]

    finally:
        connection.close()

    return render_template(
        "dashboard.html",
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        resolved_tickets=resolved_tickets
    )

@app.route("/ticket/<int:ticket_id>")
def ticket_details(ticket_id):

    connection = get_db_connection()

    try:
        ticket = connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,)
        ).fetchone()

    finally:
        connection.close()

    if ticket is None:
        return "Ticket not found", 404

    return render_template(
        "ticket_details.html",
        ticket=ticket
    )

@app.route("/delete-ticket/<int:ticket_id>", methods=["POST"])
def delete_ticket(ticket_id):

    connection = get_db_connection()

    try:
        connection.execute(
            "DELETE FROM tickets WHERE id = ?",
            (ticket_id,)
        )

        connection.commit()

    finally:
        connection.close()

    return redirect(url_for("view_tickets"))

if __name__ == "__main__":
    app.run(debug=True)
  
