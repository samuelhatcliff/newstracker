const body = document.querySelector("body");

const homeAdd = function (arg) {
    arg.classList.add("home-body");
}

const saButtons = document.querySelectorAll(".sa-button");
for (let button of saButtons) {
    button.addEventListener("click", async function (evt) {
        evt.preventDefault();
        let text = button.firstChild;
        let input = text.nextSibling;
        let value = input.value;
        let storyID = button.getAttribute('data-story')

        if (value === "Get Polarity") {
            try {
                let req = await axios.post(`/${storyID}/polarity`);
                let resp = req.data.response;
                input.value = resp;
            } catch (error) {
                console.error(error.response.data)
            }
        }
        else if (value === "Get Subjectivity") {
            let req = await axios.post(`/${storyID}/subjectivity`);
            let resp = req.data.response;
            input.value = resp;
        }
    })
}