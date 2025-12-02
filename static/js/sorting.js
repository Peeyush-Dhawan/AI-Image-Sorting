document.addEventListener('DOMContentLoaded', () => {
    const studentIdInput = document.getElementById('studentIdInput');
    const findBtn = document.getElementById('findBtn');
    const resultsGrid = document.getElementById('resultsGrid');
    const statusMessage = document.getElementById('statusMessage');

    findBtn.addEventListener('click', async () => {
        const studentId = studentIdInput.value.trim();
        if (!studentId) {
            showStatus('Please enter a Student ID', 'error');
            return;
        }

        try {
            findBtn.disabled = true;
            findBtn.textContent = 'Searching...';
            showStatus('Searching for matches...', 'info');
            resultsGrid.innerHTML = '';

            const formData = new FormData();
            formData.append('student_id', studentId);

            const response = await fetch('/sorting/find', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Search failed');
            }

            const data = await response.json();

            if (data.matches.length === 0) {
                showStatus('No matching photos found for this student.', 'info');
            } else {
                showStatus(`Found ${data.matches.length} matches!`, 'success');
                displayResults(data.matches);
            }

        } catch (error) {
            showStatus(error.message, 'error');
        } finally {
            findBtn.disabled = false;
            findBtn.textContent = 'Find Photos';
        }
    });

    function displayResults(matches) {
        resultsGrid.innerHTML = '';
        matches.forEach(match => {
            const div = document.createElement('div');
            div.className = 'result-card';
            div.innerHTML = `
                <img src="${match.imageUrl}" alt="Matched Photo" loading="lazy">
                <div class="result-info">
                    <div>Similarity: <span class="similarity-score">${(match.similarity * 100).toFixed(1)}%</span></div>
                </div>
            `;
            resultsGrid.appendChild(div);
        });
    }

    function showStatus(msg, type) {
        statusMessage.textContent = msg;
        statusMessage.className = type;
        statusMessage.classList.remove('hidden');
    }
});
