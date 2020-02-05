# Input

To start tracking, press the + button, type in the activity name in the entry, and hit the Enter key. To specify more detail on the fly, use this syntax: `time_info activity name @category, some description #tag #other tag with spaces`.

1. Specify specific times as `13:10-13:45`, and "started 5 minutes ago" as `-5`.

2. Next comes the activity name

3. Place the category after the activity name, and start it with an at sign `@`, e.g. `@garden`

4. If you want to add a description and/or tags, add a comma `,`.

5. The description is just free-form text immediately after the comma, and runs until the end of the string or until the first tag.

6. Place tags at the end, and start each tag with a hash mark `#`.

### A few examples:

- Add note on the important act of watering flowers over lunch.
>     12:30-12:45 watering flowers

- Need more tomatoes in the garden. Digging holes is purely informational, so add it as a description.
>     tomatoes@garden, digging holes

- Correct information by informing application that I've been doing something else for the last seven minutes.
>     -7 existentialism, thinking about the vastness of the universe

### Time input

Relative times work both for start time and end time, provided they are separated by a space.
`-30 -10` means started 30 minutes ago and stopped 10 minutes ago.

Times can be entered with a colon (hh:mm), with a dot (hh.mm) or just the 4 digits (hhmm).
