document.addEventListener('DOMContentLoaded', () => {
    const hostelSelect = document.getElementById('hostel');
    const studentsContainer = document.getElementById('students');

    function loadStudents(hostelName) {
        const students = studentsData[hostelName] || [];
        studentsContainer.innerHTML = '';

        students.forEach(student => {
            const label = document.createElement('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.name = present_${student};
            checkbox.value = 'present';

            label.appendChild(checkbox);
            label.append(` ${student}`);
            studentsContainer.appendChild(label);
        });
    }

    // Load students on change
    hostelSelect.addEventListener('change', () => {
        loadStudents(hostelSelect.value);
    });

    // Load students on page load
    loadStudents(hostelSelect.value);
});