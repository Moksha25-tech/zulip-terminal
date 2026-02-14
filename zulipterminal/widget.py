"""Process widgets (submessages) like polls, todo lists, etc.

This module now uses the explicit TypedDicts from
``zulipterminal.api_types`` so processing functions return strongly
typed results that mypy can validate end-to-end.
"""

import json
from typing import Any, Dict, List, Union, cast

from zulipterminal.api_types import (
    PollOption,
    PollWidgetResult,
    RawPollWidget,
    RawTodoWidget,
    Submessage,
    TodoTask,
    TodoWidgetResult,
)


def find_widget_type(submessages: List[Submessage]) -> str:
    if submessages and "content" in submessages[0]:
        content = submessages[0]["content"]

        if isinstance(content, str):
            try:
                loaded_content = json.loads(content)
                return loaded_content.get("widget_type", "unknown")
            except json.JSONDecodeError:
                return "unknown"
        return "unknown"
    return "unknown"


def process_todo_widget(todo_list: List[Submessage]) -> TodoWidgetResult:
    title: str = ""
    tasks: Dict[str, TodoTask] = {}

    for entry in todo_list:
        content = entry["content"]
        sender_id = entry["sender_id"]
        msg_type = entry["msg_type"]

        if msg_type == "widget" and isinstance(content, str):
            raw = json.loads(content)
            widget = cast(Union[RawTodoWidget, Dict[str, Any]], raw)

            if widget.get("widget_type") == "todo":
                if "extra_data" in widget and widget["extra_data"] is not None:
                    extra_data = cast(Dict[str, Any], widget["extra_data"])
                    title = cast(str, extra_data.get("task_list_title", ""))
                    if title == "":
                        title = "Task list"
                    for i, task in enumerate(extra_data.get("tasks", [])):
                        task_id = f"{i},canned"
                        tasks[task_id] = {"task": task["task"], "desc": task.get("desc", ""), "completed": False}

            elif widget.get("type") == "new_task":
                task_id = f"{widget['key']},{sender_id}"
                tasks[task_id] = {"task": widget["task"], "desc": widget.get("desc", ""), "completed": False}

            elif widget.get("type") == "strike":
                task_id = widget["key"]
                if task_id in tasks:
                    tasks[task_id]["completed"] = not tasks[task_id]["completed"]

            elif widget.get("type") == "new_task_list_title":
                title = cast(str, widget.get("title", ""))

    return {"title": title, "tasks": tasks}


def process_poll_widget(poll_content: List[Submessage]) -> PollWidgetResult:
    poll_question: str = ""
    options: Dict[str, PollOption] = {}

    for entry in poll_content:
        content = entry["content"]
        sender_id = entry["sender_id"]
        msg_type = entry["msg_type"]

        if msg_type == "widget" and isinstance(content, str):
            raw = json.loads(content)
            widget = cast(Union[RawPollWidget, Dict[str, Any]], raw)

            if widget.get("widget_type") == "poll":
                poll_question = widget["extra_data"]["question"]
                for i, option in enumerate(widget["extra_data"].get("options", [])):
                    option_id = f"canned,{i}"
                    options[option_id] = {"option": option, "votes": []}

            elif widget.get("type") == "question":
                poll_question = widget["question"]

            elif widget.get("type") == "vote":
                option_id = widget["key"]
                vote_type = widget["vote"]

                if option_id in options:
                    if vote_type == 1 and sender_id not in options[option_id]["votes"]:
                        options[option_id]["votes"].append(sender_id)
                    elif vote_type == -1 and sender_id in options[option_id]["votes"]:
                        options[option_id]["votes"].remove(sender_id)

            elif widget.get("type") == "new_option":
                idx = widget["idx"]
                new_option = widget["option"]
                option_id = f"{sender_id},{idx}"
                options[option_id] = {"option": new_option, "votes": []}

    return {"question": poll_question, "options": options}
