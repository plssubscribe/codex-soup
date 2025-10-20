const todoForm = document.querySelector('.todo-form');
const todoInput = document.getElementById('todo-input');
const todoList = document.querySelector('.todo-list');
const timerDisplay = document.querySelector('.timer-display');
const timerButtons = document.querySelectorAll('.timer-controls .btn');
const sessionSelect = document.getElementById('session-length');
const progressBar = document.querySelector('.timer-progress__bar');
const notesArea = document.getElementById('notes');
const saveNotesBtn = document.getElementById('save-notes');
const notesStatus = document.querySelector('.notes-status');
const quoteText = document.querySelector('.quote-text');
const newQuoteBtn = document.getElementById('new-quote');
const clock = document.querySelector('.taskbar__clock');

let timerInterval = null;
let remainingSeconds = 25 * 60;
let selectedSession = 25;

const QUOTES = [
  '“Success is the sum of small efforts, repeated day in and day out.” – Robert Collier',
  '“Don’t wish it were easier; wish you were better.” – Jim Rohn',
  '“Study the past if you would define the future.” – Confucius',
  '“Discipline is the bridge between goals and accomplishment.” – Jim Rohn',
  '“The secret of getting ahead is getting started.” – Mark Twain',
  '“Push yourself, because no one else is going to do it for you.” – Anonymous'
];

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
    .toString()
    .padStart(2, '0');
  const secs = Math.floor(seconds % 60)
    .toString()
    .padStart(2, '0');
  return `${mins}:${secs}`;
}

function renderTodos() {
  const items = JSON.parse(localStorage.getItem('retro98_todos') || '[]');
  todoList.innerHTML = '';

  if (!items.length) {
    const empty = document.createElement('li');
    empty.textContent = 'No tasks yet. Double-click an item to complete it!';
    empty.classList.add('todo-item');
    empty.style.justifyContent = 'center';
    empty.style.fontStyle = 'italic';
    empty.style.background = '#f4f4f4';
    todoList.appendChild(empty);
    return;
  }

  items.forEach((item, index) => {
    const li = document.createElement('li');
    li.className = `todo-item${item.completed ? ' completed' : ''}`;
    li.tabIndex = 0;
    li.dataset.index = index;

    const span = document.createElement('span');
    span.textContent = item.text;

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'btn';
    deleteBtn.type = 'button';
    deleteBtn.textContent = 'Delete';
    deleteBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      const updated = [...items];
      updated.splice(index, 1);
      localStorage.setItem('retro98_todos', JSON.stringify(updated));
      renderTodos();
    });

    li.addEventListener('dblclick', () => {
      const updated = [...items];
      updated[index].completed = !updated[index].completed;
      localStorage.setItem('retro98_todos', JSON.stringify(updated));
      renderTodos();
    });

    li.addEventListener('keyup', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        li.dispatchEvent(new Event('dblclick'));
      }
    });

    li.append(span, deleteBtn);
    todoList.appendChild(li);
  });
}

function handleTodoSubmit(event) {
  event.preventDefault();
  const value = todoInput.value.trim();
  if (!value) return;

  const items = JSON.parse(localStorage.getItem('retro98_todos') || '[]');
  const nextItems = [...items, { text: value, completed: false }];
  localStorage.setItem('retro98_todos', JSON.stringify(nextItems));
  todoInput.value = '';
  renderTodos();
}

function tickTimer() {
  if (remainingSeconds <= 0) {
    clearInterval(timerInterval);
    timerInterval = null;
    timerDisplay.textContent = '00:00';
    progressBar.style.width = '100%';
    window.alert('Time! Stretch, hydrate, and plan your next focus block.');
    return;
  }

  remainingSeconds -= 1;
  timerDisplay.textContent = formatTime(remainingSeconds);
  const progress = ((selectedSession * 60 - remainingSeconds) / (selectedSession * 60)) * 100;
  progressBar.style.width = `${Math.min(progress, 100)}%`;
}

function startTimer() {
  if (timerInterval) return;
  timerInterval = setInterval(tickTimer, 1000);
}

function pauseTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
}

function resetTimer() {
  pauseTimer();
  remainingSeconds = selectedSession * 60;
  timerDisplay.textContent = formatTime(remainingSeconds);
  progressBar.style.width = '0%';
}

function changeSession(event) {
  selectedSession = Number(event.target.value);
  resetTimer();
}

function saveNotes() {
  localStorage.setItem('retro98_notes', notesArea.value);
  notesStatus.textContent = 'Saved!';
  setTimeout(() => {
    notesStatus.textContent = '';
  }, 1800);
}

function loadNotes() {
  notesArea.value = localStorage.getItem('retro98_notes') || '';
}

function loadQuote() {
  const index = Math.floor(Math.random() * QUOTES.length);
  quoteText.textContent = QUOTES[index];
}

function updateClock() {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  clock.textContent = `${hours}:${minutes}`;
}

function init() {
  renderTodos();
  loadNotes();
  resetTimer();
  loadQuote();
  updateClock();
  setInterval(updateClock, 30_000);
}

init();

todoForm.addEventListener('submit', handleTodoSubmit);

timerButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const action = button.dataset.action;
    if (action === 'start') startTimer();
    if (action === 'pause') pauseTimer();
    if (action === 'reset') resetTimer();
  });
});

sessionSelect.addEventListener('change', changeSession);

saveNotesBtn.addEventListener('click', saveNotes);

newQuoteBtn.addEventListener('click', loadQuote);

window.addEventListener('beforeunload', saveNotes);
