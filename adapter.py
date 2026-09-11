"""OpenAI chat completions adapter. Tools get nothing from here except the model’s args."""
import json
import os
import uuid

import requests


class ToolCall:
    def __init__(self, id, name, args):
        self.id = id
        self.name = name
        self.args = args


class ModelTurn:
    def __init__(self, text='', tool_calls=None, tokens=0):
        self.text = text or ''
        self.tool_calls = tool_calls or []
        self.tokens = tokens


class ScriptedAdapter:
    """Test double: each complete() pops the next ModelTurn."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.seen = []

    def complete(self, messages, tools):
        self.seen.append((messages, tools))
        if not self.turns:
            return ModelTurn(text='stopped: no scripted turns left')
        return self.turns.pop(0)


class OpenAIAdapter:
    def __init__(self, api_key=None, model=None, timeout=None):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY', '')
        self.model = model or os.environ.get('OPENAI_MODEL') or 'gpt-4.1-mini'
        self.timeout = timeout or int(os.environ.get('FLIGHTOPS_TIMEOUT', '30'))

    def complete(self, messages, tools):
        if not self.api_key:
            raise RuntimeError('OPENAI_API_KEY is empty')
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {self.api_key}'},
            json={'model': self.model, 'messages': messages, 'tools': tools},
            timeout=self.timeout,
        )
        if not response.ok:
            detail = _openai_error(response)
            raise RuntimeError(f'OpenAI {response.status_code} model={self.model}: {detail}')
        data = response.json()
        choice = data['choices'][0]['message']
        usage = data.get('usage') or {}
        tokens = int(usage.get('total_tokens') or 0)
        calls = []
        for raw in choice.get('tool_calls') or []:
            args = raw.get('function', {}).get('arguments') or '{}'
            calls.append(ToolCall(
                id=raw.get('id') or uuid.uuid4().hex,
                name=raw.get('function', {}).get('name', ''),
                args=json.loads(args) if isinstance(args, str) else dict(args),
            ))
        return ModelTurn(text=choice.get('content') or '', tool_calls=calls, tokens=tokens)


def _openai_error(response):
    try:
        err = response.json().get('error') or {}
        return err.get('message') or response.text
    except ValueError:
        return response.text or response.reason
