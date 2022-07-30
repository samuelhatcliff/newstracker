const body = document.querySelector("body");

const homeAdd = function (arg) {
    arg.classList.add("home-body");
}

//axios requests that reach our server to run SA on said story and show result inside button
const saButtons = document.querySelectorAll(".sa-button");
for (let button of saButtons) {
    button.addEventListener("click", async function (evt) {
        evt.preventDefault();
        let text = button.firstChild;
        let input = text.nextSibling;
        let value = input.value;
        let storyID = button.getAttribute('data-story')
        console.log("TRYTYYYY", storyID)

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


//Replace broken images with default image

const default_avatar = 'https://secure.gravatar.com/avatar?d=wavatar';

window.addEventListener("load", event => {
    let images = document.querySelectorAll('img');
    for (let image of images) {
        let isLoaded = image.complete && image.naturalHeight !== 0;
        if (!isLoaded) {
            image.src = default_avatar;
        }
    }
});
// Source: https://www.techiedelight.com/replace-broken-images-with-javascript/