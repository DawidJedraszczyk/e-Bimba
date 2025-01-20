const feedbackModal = document.getElementById('feedback-modal');
const feedback = document.getElementById('feedback')
const form = document.getElementById('form');
const thanksSpan = document.getElementById('thanks');
const closeModalBtn = document.getElementById('close-feedback-modal-btn');
const description = document.getElementById("describe")

const hide_thanks_show_form = () => {
    form.style.display = 'block';
    thanksSpan.style.display = 'none';
    description.value = '';
}

document.addEventListener('DOMContentLoaded', function () {
    feedback.addEventListener('click', function () {
        feedbackModal.classList.toggle('modal')
        hide_thanks_show_form();
    })

    closeModalBtn.addEventListener('click', () => {
        feedbackModal.classList.toggle('modal');
        hide_thanks_show_form();
    })


    const sendData = async () => {
        const formData = new FormData();
        const endpoint = '/feedback/create';
        const describe = description.value;
        const currentDate = get_current_time();
        const rating = document.querySelector('input[name="star-rating"]:checked')?.value;
        const departureDetails = JSON.parse(sessionStorage.getItem('departuresDetails') || '{}');

        // Gather routeForm inputs
        const routeForm = document.getElementById('routeForm'); // Assuming the form has an id 'routeForm'
        const routeFormData = {};
        if (routeForm) {
            Array.from(routeForm.elements).forEach(input => {
                if (input.name) {
                    routeFormData[input.name] = input.value;
                }
            });
        }

        // Combine data for stored_data field
        const storedData = {
            departureDetails: departureDetails,
            routeForm: routeFormData
        };

        formData.append('description', describe);
        formData.append('timestamp', currentDate);
        formData.append('url', window.location.href);
        formData.append('rating', rating || ''); // Append rating, default to empty if none selected
        formData.append('stored_data', JSON.stringify(storedData)); // Append JSON data


        const csrfToken = getCSRFToken();

        const headers = new Headers({
            "X-CSRFToken": csrfToken
        });

        form.style.display = 'none';
        thanksSpan.style.display = 'block';

        try {
            const response = await fetch(endpoint, {
                method: 'POST', body: formData, headers: headers,
            });
            if (!response.ok) {
                console.error('Error sending data:', response.statusText);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    const get_current_time = () => {
        const current_date = new Date();
        const iso_formatted_time = current_date.toISOString();
        return iso_formatted_time.slice(0, -5) + "Z";
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        sendData();
    })
});

function getCSRFToken() {
    const name = "csrftoken";
    const cookieValue = document.cookie.match(`(^|;)\\s*${name}\\s*=([^;]+)`);
    return cookieValue ? cookieValue.pop() : '';
}