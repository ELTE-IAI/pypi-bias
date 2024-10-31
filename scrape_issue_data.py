"""
This script scrapes the pypi/support issue tracker and creates a dataframe
pep541_full at the end. This is a pd.DataFrame with:

rows = PEP 541 support requests - all recorded on the issue tracker

columns = metadata of support request, including

* state - state of the issue, "open" or "closed"
* created_at - date the issue was opened
* closed_at - date the issue was closed, if closed, otherwise nan
* duration - difference closed_at - created_at
* duration_D - duration rounded to days
* user_ID - GitHub user ID
* real_name - real name displayed on GitHub profile
* location - location displayed on GitHub profile

Requirements:

* optional: enter GitHub token in get_user_info, "Authorization" field.
  This uses an authenticated GitHub account to avoid request limits for anonymous.
* python environment with packages as below

beautiful soup
pandas
requests
"""

import requests
import pandas as pd

# Define the GitHub repository and label
repo = "pypi/support"


def get_all_pypi_issues(repo):
    # GitHub API URL for issues
    url = f"https://api.github.com/repos/{repo}/issues"

    # Parameters to filter the issues by label
    params = {
        "state": "all",  # Fetch both open and closed issues
        "per_page": 100,  # Maximum per page
    }

    # Request headers (optional)
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }

    # Fetching the data
    issues = []
    while url:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an error for bad requests
        issues.extend(response.json())
        url = response.links.get("next", {}).get("url")  # Check if there's a next page
    return issues


def is_pep541(issue):
    labels = issue.get("labels", None)

    if labels is None:
        return False
    if not isinstance(labels, list):
        return False
    if len(labels) == 0:
        return False
    labels = labels[0]
    if not isinstance(labels, dict):
        return False
    return labels.get("description", "") == "Package name support requests"


# Function to get the real name and location of a user
def get_user_info(username):
    # token = "foo"
    headers = {
       "Accept": "application/vnd.github.v3+json",
       # "Authorization": f"Bearer {token}",
    }
    user_url = f"https://api.github.com/users/{username}"
    user_response = requests.get(user_url, headers=headers)
    user_response.raise_for_status()
    user_data = user_response.json()
    return user_data.get('name', username), user_data.get('location', 'Unknown')  # Default if not available


def get_user_info_bs(username):
    from bs4 import BeautifulSoup

    user_url = f"https://github.com/{username}"
    user_response = requests.get(user_url)
    user_response.raise_for_status()

    soup = BeautifulSoup(user_response.text, 'html.parser')
    
    name = soup.find('span', class_='p-name vcard-fullname d-block overflow-hidden')
    location = soup.find('span', class_='p-label')
    
    real_name = name.text.strip() if name else username
    location = location.text.strip() if location else 'Unknown'
    
    return real_name, location


all_pypi_issues = get_all_pypi_issues(repo)
issues_pep541 = [issue for issue in all_pypi_issues if is_pep541(issue)]

issues_state = [issue["state"] for issue in issues_pep541]
issues_created_at = [issue["created_at"] for issue in issues_pep541]
issues_closed_at = [issue["closed_at"] for issue in issues_pep541]
issues_user_id = [issue["user"]["login"] for issue in issues_pep541]
issues_user_info = [get_user_info(user_id) for user_id in issues_user_id]
issues_user_name = [x[0] for x in issues_user_info]
issues_user_loc = [x[1] for x in issues_user_info]

pep541_full = pd.DataFrame(
    {
        "state": issues_state,
        "created_at": issues_created_at,
        "closed_at": issues_closed_at,
        "user_id": issues_user_id,
        "real_name": issues_user_name,
        "location": issues_user_loc
    }
)

pep541_full['created_at'] = pd.to_datetime(pep541_full['created_at'], errors='coerce').dt.tz_localize(None)
pep541_full['closed_at'] = pd.to_datetime(pep541_full['closed_at'], errors='coerce').dt.tz_localize(None)

def split_last_name(name):
    if name is None:
        return None
    parts = str(name).strip().split()
    last_name = parts[-1] if len(parts) > 0 else ''
    return last_name

def split_first_name(name):
    if name is None:
        return None
    parts = str(name).strip().split()
    first_name = parts[0] if len(parts) > 0 else ''
    return first_name

pep541_full['last_name'] = pep541_full['real_name'].map(split_last_name)
pep541_full['first_name'] = pep541_full['real_name'].map(split_first_name)
pep541_full["duration"] = pep541_full["closed_at"] - pep541_full["created_at"]
pep541_full["duration_D"] = pep541_full["duration"].dt.days

# optional: save pep541_full to local csv
