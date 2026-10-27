# English website and consumer arrival entry

User requested an English website and a consumer-friendly date/time input. Prior approval delegates implementation details without further confirmation.

- Translate all built-in UI labels, accessibility text, evaluation explanations, errors and map fallbacks. Preserve existing user-entered data and Korean developer field comments.
- Replace raw ISO text entry with native date and time controls. Explicit Pacific time (BC) default, optional UTC. Convert entered local time to an aware instant on the server; API and legacy aware URLs remain compatible.
- Preserve submitted values on errors, use a server-side Search now action, and keep SSR/no-JS behavior. Reject incomplete, nonexistent or ambiguous local times with helpful English messages. Show readable date/time summaries.
- Test English-rendered pages, conversion, legacy URLs, validation/value restoration, same instant in detail, no-JS calendar entry and mobile layout. Run full suite and review the changed code before restart/preview.

Tasks: UI translation agent; domain/DAL messages agent; root arrival parsing/forms/styles/tests/integration. File ownership disjoint.
