import json
import os
import socket
import ssl
import uuid
import urllib.request
import urllib.parse
import urllib.error

BASE_URL = "https://silastali.su"


class ApiError(Exception):
    def __init__(self, message, status=0):
        super().__init__(message)
        self.status = status


class Api:
    def __init__(self):
        self.token = None

    def _url(self, path):
        return BASE_URL + path

    def _request(self, method, path, data=None, params=None, form=None, raw=False):
        url = self._url(path)
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {}
        body = None
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if form is not None:
            body = urllib.parse.urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                content = resp.read().decode("utf-8")
                if raw:
                    return content
                try:
                    return json.loads(content) if content else None
                except ValueError:
                    return content
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", errors="replace")
            detail = ""
            try:
                detail = json.loads(msg).get("detail", "")
            except ValueError:
                detail = msg
            raise ApiError(detail or f"Ошибка сервера ({e.code})", e.code) from None
        except urllib.error.URLError as e:
            raise ApiError("Нет соединения с сервером: " + str(e.reason)) from None

    # ---- auth ----
    def login(self, username, password):
        return self._request("POST", "/auth/login", form={
            "username": username,
            "password": password,
        })

    def login_chief(self, password):
        return self._request("POST", "/auth/login-chief", form={
            "password": password,
        })

    def me(self):
        return self._request("GET", "/auth/me")

    def get_employees(self, block=None):
        url = "/auth/employees"
        if block:
            url += f"?block={block}"
        return self._request("GET", url)

    # ---- users ----
    def get_users(self):
        return self._request("GET", "/users")

    def create_user(self, username, password, full_name, role, block=None):
        data = {
            "username": username,
            "password": password,
            "full_name": full_name,
            "role": role,
        }
        if block:
            data["block"] = block
        return self._request("POST", "/users", data=data)

    def update_user(self, user_id, **fields):
        return self._request("PUT", f"/users/{user_id}", data=fields)

    def delete_user(self, user_id):
        return self._request("DELETE", f"/users/{user_id}")

    def update_me(self, current_password, new_username=None, new_password=None):
        data = {"current_password": current_password}
        if new_username:
            data["new_username"] = new_username
        if new_password:
            data["new_password"] = new_password
        return self._request("PUT", "/users/me", data=data)

    # ---- works ----
    def get_works(self, date_from=None, date_to=None, worker_id=None, part_number=None):
        params = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if worker_id:
            params["worker_id"] = worker_id
        if part_number:
            params["part_number"] = part_number
        return self._request("GET", "/works", params=params)

    def get_my_works(self):
        return self._request("GET", "/works/my")

    def create_work(self, part_number, quantity, note, start_time, end_time=None):
        data = {
            "part_number": part_number,
            "quantity": quantity,
            "note": note,
            "start_time": start_time,
        }
        if end_time:
            data["end_time"] = end_time
        return self._request("POST", "/works", data=data)

    def delete_work(self, work_id):
        return self._request("DELETE", f"/works/{work_id}")

    # ---- stats ----
    def stats_overview(self, date_from=None, date_to=None):
        params = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return self._request("GET", "/stats/overview", params=params)

    def stats_by_worker(self, date_from=None, date_to=None):
        params = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return self._request("GET", "/stats/by-worker", params=params)

    def stats_timeline(self, group_by, date_from=None, date_to=None):
        params = {"group_by": group_by}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return self._request("GET", "/stats/timeline", params=params)

    def stats_my(self, date_from=None, date_to=None, group_by="day"):
        params = {"group_by": group_by}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return self._request("GET", "/stats/my", params=params)

    def export_url(self, date_from=None, date_to=None):
        path = "/export/excel"
        params = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return self._url(path) + ("?" + urllib.parse.urlencode(params) if params else "")

    # ---- orders ----
    def get_orders(self, status=None, block=None):
        params = {}
        if status:
            params["status"] = status
        if block:
            params["block"] = block
        return self._request("GET", "/orders", params=params)

    def get_order(self, order_id):
        return self._request("GET", f"/orders/{order_id}")

    def _multipart(self, path, filepath):
        url = self._url(path)
        with open(filepath, "rb") as f:
            content = f.read()
        boundary = "sila-stali-" + uuid.uuid4().hex
        filename = os.path.basename(filepath)
        head = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f'Content-Type: application/octet-stream\r\n\r\n'
        ).encode("utf-8")
        tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
        body = head + content + tail
        headers = {
            "Authorization": "Bearer " + (self.token or ""),
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", errors="replace")
            detail = ""
            try:
                detail = json.loads(msg).get("detail", "")
            except ValueError:
                detail = msg
            raise ApiError(detail or f"Ошибка сервера ({e.code})", e.code) from None
        except urllib.error.URLError as e:
            raise ApiError("Нет соединения с сервером: " + str(e.reason)) from None

    def upload_order(self, filepath):
        return self._multipart("/orders/upload", filepath)

    def complete_item(self, order_id, item_id, quantity, executor_id=None, note=None, stage=None):
        data = {"quantity": quantity}
        if executor_id:
            data["executor_id"] = executor_id
        if note:
            data["note"] = note
        if stage:
            data["stage"] = stage
        return self._request("POST", f"/orders/{order_id}/items/{item_id}/complete", data=data)

    def claim_item(self, order_id, item_id, executor_id=None):
        data = {}
        if executor_id:
            data["executor_id"] = executor_id
        return self._request("POST", f"/orders/{order_id}/items/{item_id}/claim", data=data)

    def release_item(self, order_id, item_id):
        return self._request("DELETE", f"/orders/{order_id}/items/{item_id}/claim")

    def add_claim_participant(self, order_id, item_id, worker_id):
        return self._request(
            "POST",
            f"/orders/{order_id}/items/{item_id}/claim/participants",
            data={"executor_id": worker_id},
        )

    def remove_claim_participant(self, order_id, item_id, worker_id):
        return self._request(
            "DELETE",
            f"/orders/{order_id}/items/{item_id}/claim/participants/{worker_id}",
        )

    def delete_completion(self, completion_id):
        return self._request("DELETE", f"/orders/completions/{completion_id}")

    def mark_order_ready(self, order_id):
        return self._request("POST", f"/orders/{order_id}/ready", data={})

    def delete_order(self, order_id):
        return self._request("DELETE", f"/orders/{order_id}")

    def close_order(self, order_id):
        return self._request("POST", f"/orders/{order_id}/close", data={})

    def order_stats(self, date_from=None, date_to=None):
        params = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return self._request("GET", "/orders/stats/list", params=params)

    def order_stats_my(self, date_from=None, date_to=None):
        params = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return self._request("GET", "/orders/stats/my", params=params)

    # ---- crew invites ----
    def get_crew_invites(self):
        return self._request("GET", "/crew-invites")

    def respond_invite(self, invite_id, accept):
        return self._request("POST", f"/crew-invites/{invite_id}/respond",
                             data={"accept": bool(accept)})

    # ---- chat ----
    def get_chats(self):
        return self._request("GET", "/chat/list")

    def get_chat_messages(self, chat_id, after_id=0, limit=200):
        params = {"after_id": after_id, "limit": limit}
        return self._request("GET", f"/chat/{chat_id}/messages", params=params)

    def send_chat_message(self, chat_id, text):
        return self._request("POST", f"/chat/{chat_id}/messages", data={"text": text})

    def create_dm(self, user_id):
        return self._request("POST", "/chat/dm", data={"user_id": user_id})

    def create_chat(self, name, member_ids):
        return self._request("POST", "/chat/create", data={"name": name, "member_ids": member_ids})

    def mark_chat_read(self, chat_id, last_message_id):
        return self._request("POST", f"/chat/{chat_id}/read", data={"last_message_id": last_message_id})

    def add_chat_members(self, chat_id, user_ids):
        return self._request("POST", f"/chat/{chat_id}/members", data={"user_ids": user_ids})

    def leave_chat(self, chat_id):
        return self._request("DELETE", f"/chat/{chat_id}/members/me")