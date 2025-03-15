
import requests
import json
import sys
import asyncio

async def fetch_group_list(token):
    """
    Validate token and fetch groups from Facebook Messenger.
    Returns a list of groups or an error message.
    """
    url = "https://graph.facebook.com/v17.0/me/conversations"
    params = {
        'access_token': token,
        'fields': 'name,id'
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if 'error' in data:
            return {"error": data['error']['message']}

        conversations = data.get('data', [])
        if not conversations:
            return {"error": "No conversations found. Check your token permissions."}

        # Format conversations
        formatted_conversations = []
        for conv in conversations:
            name = conv.get('name', 'Unnamed Chat')
            tid = conv['id'].replace('t_', '')  # Remove 't_' prefix if present
            formatted_conversations.append({
                'id': tid,
                'name': name
            })

        return formatted_conversations

    except requests.exceptions.RequestException:
        return {"error": "Network error. Check your internet connection."}
    except Exception as e:
        return {"error": str(e)}
