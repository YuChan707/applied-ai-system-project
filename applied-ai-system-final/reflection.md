# PawPal+ Project Reflection
## Student Yuzhen Chen
## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?
+ The Owner class represents the user and stores their available time and preferences.
The Pet class represents the pet and is linked to the owner. It keeps basic information like name and type.
+ The Task class represents pet care activities such as walking or feeding, including duration and priority.
+ The Planner class is the main logic component. It organizes tasks, applies constraints, and generates a daily schedule based on priority and available time.
+ The Schedule class represents the final plan, storing the selected tasks and total time, and can display or explain the plan.


**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.
BY my side planning. Yes, in the task, I decide to associate a assigment with the owner name because as each pet are different (and usually match with the owner personality). They could be associate with their special task.

__________________________________________________
AI responses: 
Structure & Design — Good

All 5 classes from your UML are present with correct attributes and method signatures.
Type hints are consistent throughout.
raise NotImplementedError is the right pattern for stubs — it signals intent and fails loudly.
Planner.__init__ defaulting constraints to {} is a good defensive default.

Design gap — missing link

Planner.generate_schedule takes a flat tasks list, but tasks live on Pet objects. Nothing collects them. You'll need either:

a helper that gathers tasks from owner.pets, or
pass owner directly into generate_schedule instead of tasks.
Minor

Task.update_priority (line 11) is marked optional in your spec. If you don't plan to implement it, you can drop it to keep the class simpler.
The class order in the file (Task → Pet → Owner → Schedule → Planner) is good — dependencies are defined before they're used.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

+ The planner employs an approach that selects tasks in order of priority and stops once the allotted time runs out. This means it might skip a brief, low-priority task simply because a longer, high-priority task consumed the remaining minutes first.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
+ As the pet care application, as failing to complete a high-priority task (such as feeding) is always worse than skipping a low-priority one (such as environmental enrichment).

- Why is that tradeoff reasonable for this scenario?
+ A pet owner would prefer to correctly complete the most important tasks rather than attempting to squeeze everything in and running the risk of running out of time halfway through a walk.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
Mentoring, understand the logic behind and brainstorms the idea (polish/plain languege)

- What kinds of prompts or questions were most helpful?
using W question, why/when/how and giving definition behind

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
when describe me the conflict schedule. Giving all possible cases, I added more on my own.

- How did you evaluate or verify what the AI suggested?
I qualify 85 of 100 because it's problme the structure idea but it's lose the context behind.
---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
Task completion changes status — after calling mark_complete(), the task's completed field switches from False to True
Adding a task increases the pet's task count — after calling add_task(), len(pet.tasks) goes up by exactly 1 each time

- Why were these tests important?
The two automated tests targeted the most foundational behaviors — if mark_complete() doesn't actually flip the status, the auto-reschedule logic silently breaks because mark_complete() depends on setting self.completed = True first. If add_task() doesn't grow the list, the entire scheduler has nothing to work with.

**b. Confidence**

- How confident are you that your scheduler works correctly?
80% secure because it's count all taks and utilize logic (time/priority/extra detail) that meansure what is the importants taks (on top priority)

- What edge cases would you test next if you had more time?
Edge case in the time in the task

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
The logic behind (prioritize) the taks which works

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
Adding graph or a table that display the schedule (complex)

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
Content communication, like temawork (people or AI)


System Design:
In the png and txt file named UML.
But main requirement are: name of the owner, pet information, task information, schedule and function that make the plan
