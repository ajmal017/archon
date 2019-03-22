""" mailgun """
import requests

def send_simple_message(abroker, subject, text):
    apikey = abroker.mail_api_key
    domain = abroker.mail_domain
    email_from = abroker.email_from
    email_to = abroker.email_to
    print ("send message")
    r = requests.post(
        domain,
        auth=("api", apikey),
        data={"from": email_from,
              "to": email_to,
              "subject": subject,
              "text": text})
    print (r.text)

def send_mail_html(abroker, email_from, email_to, subject, html):
    try:
        apikey = abroker.mail_api_key
        domain = abroker.mail_domain
        #email_from = abroker.email_from
        #email_to = abroker.email_to
        r = requests.post(
            domain,
            auth=("api", apikey),
            data={
                    "from": email_from,
                    "to": email_to,
                    "subject": subject,
                    "text": "",
                    "html": html
                    #"inline": images
            })
        print (r)
        print (r.content)
        return r
    except Exception as e:
        print (e)