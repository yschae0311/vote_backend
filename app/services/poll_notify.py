from app.services.poll_events import schedule_poll_event


def notify_poll_updated(poll_id: int) -> None:
    schedule_poll_event(poll_id, "poll_updated")


def notify_results_updated(poll_id: int) -> None:
    schedule_poll_event(poll_id, "results_updated")


def notify_voters_updated(poll_id: int) -> None:
    schedule_poll_event(poll_id, "voters_updated")
