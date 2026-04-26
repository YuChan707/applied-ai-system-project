from pawpal_system import Task, Pet


def test_mark_complete_changes_status():
    task = Task("Morning walk", "30-min walk", 30, "high", "walking")
    assert task.completed == False
    task.mark_complete()
    assert task.completed == True


def test_add_task_increases_pet_task_count():
    pet = Pet("Mochi", "dog", 3)
    assert len(pet.tasks) == 0
    pet.add_task(Task("Morning walk", "30-min walk", 30, "high", "walking"))
    assert len(pet.tasks) == 1
    pet.add_task(Task("Feed breakfast", "1 cup dry food", 10, "high", "feeding"))
    assert len(pet.tasks) == 2
