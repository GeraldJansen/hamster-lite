# Splitting and merging activities

Time Tracker does its best to avoid overlaps in activities. If you create an activity whose start and end time both lie within an existing activity, the existing activity will be split into two. In other cases of overlapping, the previous entries will be shrunk.

> _**BUG** Former ongoing activity not split._
> The former ongoing activity is not "split into two" actually, but merely shortened to end when the new activity starts. Reported as issue [#396](https://github.com/projecthamster/hamster/issues/396).

**TIP:** Merging can become handy when entering information for the whole day. Start by entering the first activity with only a start time (i.e. activity "in progress"). For the next activity again set just the start time. Observe how the end time of the previous activity gets adjusted to the start time of the new one. Repeat the process until happy!