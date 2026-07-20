from jinja2 import Template


# Email HTML Template
email_template = """
<!DOCTYPE html>
<html>

<head>
    <title>Interview Invitation</title>
</head>

<body>

<h2>Hello {{ name }},</h2>

<p>
You are invited for an interview.
</p>

<p>
<b>Interview Time:</b> {{ interview_time }}
</p>

<p>
<b>Interview Link:</b> {{ link }}
</p>

<p>
Regards,<br>
HR Team
</p>

</body>

</html>
"""


# Create Jinja2 Template
template = Template(email_template)


# Recipient Data
recipients = [
    {
        "name": "Sai",
        "interview_time": "10:00 AM",
        "link": "https://meet.com/sai"
    },

    {
        "name": "Rahul",
        "interview_time": "12:30 PM",
        "link": "https://meet.com/rahul"
    },

    {
        "name": "Priya",
        "interview_time": "3:00 PM",
        "link": "https://meet.com/priya"
    }
]


# Generate Dynamic Emails
for person in recipients:

    result = template.render(
        name=person["name"],
        interview_time=person["interview_time"],
        link=person["link"]
    )

    print("==============================")
    print("Generated Email")
    print("==============================")

    print(result)