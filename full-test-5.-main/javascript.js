// Import Firebase functions
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-app.js";
import { getStorage, ref, getDownloadURL, listAll } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-storage.js";

// Declare startTimer globally
let startTimer = null;

// Timer-related variables
let totalMinutes = 181; // 181 minutes
let timeLeft = totalMinutes * 60; // Convert to seconds
let timerId;
let timerKey = 'FULL TEST 6'; // Unique key for the 120-min timer
let timeDetailMessage = ""; // Global variable to store time details

// Check if time exists in localStorage
if (localStorage.getItem(timerKey)) {
    timeLeft = parseInt(localStorage.getItem(timerKey), 10);
}

// Function to start the timer
startTimer = function () {
    if (!document.getElementById('time_left')) return; // ✅ Prevents error on `index.html`
    
    timerId = setInterval(function () {
        let minutes = Math.floor(timeLeft / 60);
        let seconds = timeLeft % 60;

        // Display the timer
        document.getElementById('time_left').innerHTML = `Time Left: ${minutes}m ${seconds < 10 ? '0' : ''}${seconds}s`;

        // Save the time left in localStorage
        localStorage.setItem(timerKey, timeLeft);

        if (timeLeft <= 0) {
            clearInterval(timerId);
            autoSubmit();
            localStorage.removeItem(timerKey);
        }

        timeLeft--;
    }, 1000);
};

// Function to stop the timer
function stopTimer() {
    clearInterval(timerId);
    localStorage.removeItem(timerKey);

    const totalSeconds = totalMinutes * 60;
    const timeTakenSeconds = totalSeconds - timeLeft;
    const minutesTaken = Math.floor(timeTakenSeconds / 60);
    const secondsTaken = timeTakenSeconds % 60;

    timeDetailMessage = `Test duration: ${totalMinutes} minutes. Time taken: ${minutesTaken} minutes and ${secondsTaken} seconds.`;
    console.log(timeDetailMessage);
}

// Function to handle auto submission
function autoSubmit() {
    alert("Time is over! Submitting the test automatically.");
    document.getElementById('submit').click();
}

// ✅ Ensure this runs only if `time_left` exists
window.onload = function () {
    if (document.getElementById('time_left')) {
        startTimer();
    }
};

// ✅ Ensure `submit` button exists before attaching event listener
document.addEventListener("DOMContentLoaded", function () {
    let submitButton = document.getElementById('submit');
    if (submitButton) {
        submitButton.onclick = stopTimer;
    }
});
// Login handler (assuming there's a login form)
export function handleLogin(event) {
    event.preventDefault(); // Prevent form submission
    console.log("Login function triggered");

    const userId = document.getElementById('userId').value;
    const password = document.getElementById('password').value;

    // Basic validation to check if the fields are filled
    if (userId === "" || password === "") {
        alert("Please fill in both the ID and Password.");
        return false;
    }

    // Object with valid usernames and their respective passwords
    const validCredentials = {
        "ROHIT01": "ROHIT01",
        "ABHINAV01":"ABHINAV01",
        "ARYAN01": "ARYAN01",
        "SAMPAUL01": "SAMPAUL01",
        "ARZOO01": "ARZOO01",
        "ANSH01": "ANSH01",
        "VINEET01": "VINEET01",
        "HARSH01": "HARSH01",
        "jee2025": "jee2025",
        "jee02": "124",
        "jee03": "125",
        "jee04": "126",
        "SHANTANU01": "SHANTANU01"
    };

    // Check if the entered username exists in the object and if the password matches
    if (validCredentials[userId] && validCredentials[userId] === password) {
        // If login is successful
        window.location.href = "exam.html"; // Redirect to another page
    } else {
        // If login fails
        alert("Invalid Username or Password. Hands' up, you are going to be arrested!");
    }
}

document.addEventListener('DOMContentLoaded', function () {
    let currentSection = "phySec1"; // Default section
    let quizSubmitted = false; // Track whether the quiz has been submitted

    const sectionData = {
        phySec1: [],
        phySec2: [],
        chemSec1: [],
        chemSec2: [],
        mathsSec1: [],
        mathsSec2: []
        // bioSec1: []
    };
    
    // Function to generate URLs based on question number
    function generateUrl(section, questionNumber) {
        return `https://firebasestorage.googleapis.com/v0/b/mentorsmantratestportal1.appspot.com/o/${section}%2F${questionNumber}.jpeg?alt=media`;
    }
    
    // Populate phySec1
    for (let i = 1; i <= 20; i++) {
        sectionData.phySec1.push({
            questionNumber: i,
            url
            //  : i === 2 
            //    ? "https://firebasestorage.googleapis.com/v0/b/mentorsmantratestportal1.appspot.com/o/WPE%20%2B%20CIRCULAR%20MAINS%20TEST%2FCOM%20ADV%20QUES%2F1.jpeg?alt=media&token=e7d8978a-7339-4eb2-b791-bf7c5f205686"
            : generateUrl('Phyfulltest5', i),  // Default URL for other questions
            options
            // : i === 1 ? ["3", "6", "9", "12"]
            : i === 3 ? ["(c) and (d)", "(b) and (c)", "(a) and (b)", "(b) and (d)"]
            : ["A", "B", "C", "D"], // Custom options for question 2
            correctAnswer: [
              /*1*/ "A",
/*2*/ "C",
/*3*/ "(c) and (d)",
/*4*/ "D",
/*5*/ "A",
/*6*/ "D",
/*7*/ "A",
/*8*/ "B",
/*9*/ "A",
/*10*/ "C",
/*11*/ "B",
/*12*/ "A",
/*13*/ "B",
/*14*/ "B",
/*15*/ "D",
/*16*/ "D",
/*17*/ "B",
/*18*/ "C",
/*19*/ "D",
/*20*/ "C",
                ][i - 1]  // Adjust correct answers as needed
        });
    }
    
    // Populate phySec2
    const phySec2CorrectAnswers = [
        /*1*/ 28.28,
        /*2*/ 80,
        /*3*/ 7.50,
        /*4*/ 5.00,
        /*5*/ 0.50];
    for (let i = 21; i <= 25; i++) {
        sectionData.phySec2.push({
            questionNumber: i,
            url: generateUrl('Phyfulltest5', i),
            correctAnswer: phySec2CorrectAnswers[i - 21] // Adjusting the index to start from 0
        });
    }
    
    // // Populate chemSec1
    for (let i = 1; i <= 20; i++) {
        sectionData.chemSec1.push({
            questionNumber: i,    
             url
            //  : i === 2 
            //    ? "https://firebasestorage.googleapis.com/v0/b/mentorsmantratestportal1.appspot.com/o/WPE%20%2B%20CIRCULAR%20MAINS%20TEST%2FCOM%20ADV%20QUES%2F1.jpeg?alt=media&token=e7d8978a-7339-4eb2-b791-bf7c5f205686"
            : generateUrl('Chemfulltest5', i),  // Default URL for other questions
            options
            // : i === 3 ? ["(III)>(II)>(I)=(IV)>(V)=(VI)", "(III)>(I)>(II)=(IV)>(V)=(VI)", "(III)>(II)>(I)=(IV)>(V)=(VI)", "(III)>(I)>(IV)>(V)>(II)>(VI)"]
            : ["A", "B", "C", "D"], // Custom options for question 2
            correctAnswer: [
                /*1*/ "B",
                /*2*/ "C",
                /*3*/ "B",
                /*4*/ "C",
                /*5*/ "B",
                /*6*/ "A",
                /*7*/ "B",
                /*8*/ "B",
                /*9*/ "C",
                /*10*/ "A",
                /*11*/ "B",
                /*12*/ "C",
                /*13*/ "D",
                /*14*/ "B",
                /*15*/ "D",
                /*16*/ "A",
                /*17*/ "D",
                /*18*/ "B",
                /*19*/ "D",
                /*20*/ "D"
                            ][i - 1] // Adjust correct answers as needed
        });
    }

    //     // Populate chemSec2
        const chemSec2CorrectAnswers = [
            /*1*/ 70,
            /*2*/ 3,
            /*3*/ 5,
            /*4*/ 4,
            /*5*/ 2];
        for (let i = 21; i <= 25; i++) {
            sectionData.chemSec2.push({
                questionNumber: i,
                url: generateUrl('Chemfulltest5', i),
                correctAnswer: chemSec2CorrectAnswers[i - 21] // Adjusting the index to start from 0
            });
        }
        // Populate mathsSec1
    for (let i = 1; i <= 20; i++) {
        sectionData.mathsSec1.push({
            questionNumber: i,
            url: generateUrl('Mathsfulltest5', i),
            options
            // : i === 5 ? ["(1)", "(2)", "(3)", "(4)"] 
            :["A", "B", "C", "D"],
            correctAnswer: [
/*1*/ "B",  
/*2*/ "B",  
/*3*/ "A",  
/*4*/ "C",  
/*5*/ "D",  
/*6*/ "B",  
/*7*/ "A",  
/*8*/ "A",  
/*9*/ "A",  
/*10*/ "D",  
/*11*/ "B",
/*12*/ "A",
/*13*/ "A",
/*14*/ "B",
/*15*/ "A",
/*16*/ "B",
/*17*/ "C",
/*18*/ "B",
/*19*/ "B",
/*20*/ "C"


            ][i - 1]  // Adjust correct answers as needed
        });
    }
    
     // Populate mathsSec2
    const mathsSec2CorrectAnswers = [
        /*1*/ 9,
        /*2*/ 15.00,
        /*3*/ 2,
        /*4*/ 3,
        /*5*/ 4];
    for (let i = 21; i <= 25; i++) {
        sectionData.mathsSec2.push({
            questionNumber: i,
            url: generateUrl('Mathsfulltest5', i),
            correctAnswer: mathsSec2CorrectAnswers[i - 21] // Adjusting the index to start from 0
        });
        }
    const sectionQuestionIndex = {
        phySec1: 0,
        phySec2: 0,
        chemSec1: 0,
        chemSec2: 0,
        mathsSec1: 0,
        mathsSec2: 0
    };

    const selectedAnswers = {};
    const markedForReview = {}; // New object to track marked for review
    const isVisited = {};
    const smarkedForReview = {};
    let nselectedAnswers=0;
    let nmarkedForReview=0;
    let nisVisited=0;
    let nsmarkedForReview=0;

    // Add the getAnswersData function here
function getAnswersData() {
    const userAnswers = [];
    const correctAnswers = [];

    // Iterate through each section
    Object.keys(sectionData).forEach(section => {
        sectionData[section].forEach((question, index) => {
            // Get the user's answer (if any)
            const userAnswer = selectedAnswers[section] ? selectedAnswers[section][index] : null;
            userAnswers.push(userAnswer);

            // Get the correct answer
            const correctAnswer = question.correctAnswer;
            correctAnswers.push(correctAnswer);
        });
    });

    return {
        selectedAnswers: userAnswers,
        correctAnswers: correctAnswers
    };
}

    const saveButton = document.getElementById('favourite');
    const saveAndNextButton = document.getElementById('next');
    const smarkforreviewAndNextButton = document.getElementById('smfran');
    const markforreviewAndNextButton = document.getElementById('mfran');
    const clearResponseButton = document.getElementById('cr');
    const previousButton = document.getElementById('previous');
    const unsNextButton = document.getElementById('next_u');


    const submitButton = document.getElementById('submit'); // Assuming there's a submit button

    saveButton.addEventListener('click', saveCurrentQuestion);
    saveAndNextButton.addEventListener('click', saveAndNextQuestion);
    markforreviewAndNextButton.addEventListener('click', markforreviewAndNextQuestion);
    smarkforreviewAndNextButton.addEventListener('click', smarkforreviewAndNextQuestion);
    clearResponseButton.addEventListener('click', clearResponse);
    previousButton.addEventListener('click', goToPreviousQuestion);
    unsNextButton.addEventListener('click', goToNextQuestion);
    submitButton.addEventListener('click', submitQuiz);

    function saveCurrentQuestion() {
        if (currentSection.includes("Sec2")) {
            // For Section 2, save numerical answer
            const numericalAnswer = document.getElementById('numerical-answer').value;
    
            if (numericalAnswer) {
                if (!selectedAnswers[currentSection]) {
                    selectedAnswers[currentSection] = {};
                }
                if(!selectedAnswers[currentSection][sectionQuestionIndex[currentSection]]){
                    nselectedAnswers++;
                }
                selectedAnswers[currentSection][sectionQuestionIndex[currentSection]] = numericalAnswer;
            }
            
        } else {
            // For Section 1, save MCQ answers as before
            const selectedOption = document.querySelector(`input[name="option${sectionQuestionIndex[currentSection]}"]:checked`);
    
            if (selectedOption) {
                if (!selectedAnswers[currentSection]) {
                    selectedAnswers[currentSection] = {};
                }
                if(!selectedAnswers[currentSection][sectionQuestionIndex[currentSection]]){
                    nselectedAnswers++;
                }
                selectedAnswers[currentSection][sectionQuestionIndex[currentSection]] = selectedOption.value;
            }
        }
    
        updatePaletteItems();
    }
    

    function markforreviewAndNextQuestion() {
        // Initialize the review tracking for the current section if not already done
        if (!markedForReview[currentSection]) {
            markedForReview[currentSection] = {};
        }
        
        // Set the current question as marked for review
        if(!markedForReview[currentSection][sectionQuestionIndex[currentSection]]){
            nmarkedForReview++;
        }
        markedForReview[currentSection][sectionQuestionIndex[currentSection]] = true;
        
        
        updatePaletteItems(); // Update the palette to reflect the change
        
        goToNextQuestion();
    }

    function smarkforreviewAndNextQuestion(){
        saveCurrentQuestion();

        if (!smarkedForReview[currentSection]) {
            smarkedForReview[currentSection] = {};
        }
        
        // Set the current question as marked for review
        if(!smarkedForReview[currentSection][sectionQuestionIndex[currentSection]]){
            nsmarkedForReview++;
        }
        smarkedForReview[currentSection][sectionQuestionIndex[currentSection]] = true;
        
        updatePaletteItems(); // Update the palette to reflect the change
        
        goToNextQuestion();
    }

    function saveAndNextQuestion() {
        saveCurrentQuestion();

        if (!markedForReview[currentSection]) {
            markedForReview[currentSection] = {};
        }
        if (!smarkedForReview[currentSection]) {
            smarkedForReview[currentSection] = {};
        }
        if(markedForReview[currentSection][sectionQuestionIndex[currentSection]]){
            nmarkedForReview--;
        }
        markedForReview[currentSection][sectionQuestionIndex[currentSection]] = false;
        if(smarkedForReview[currentSection][sectionQuestionIndex[currentSection]]){
            smarkedForReview[currentSection][sectionQuestionIndex[currentSection]] = true;
        }
        
        goToNextQuestion();
    }

    function goToNextQuestion() {
        const currentIndex = sectionQuestionIndex[currentSection];
        if (currentIndex < sectionData[currentSection].length - 1) {
            sectionQuestionIndex[currentSection]++;
            updateQuestionDisplay();
            updatePaletteItems(); // Update palette colors
        } else {
            const nextSection = getNextSection();
            if (nextSection) {
                switchSection(nextSection);
            }
        }
    }

    function goToPreviousQuestion() {
        const currentIndex = sectionQuestionIndex[currentSection];
        if (currentIndex > 0) {
            sectionQuestionIndex[currentSection]--;
            updateQuestionDisplay();
            updatePaletteItems(); // Update palette colors
        }
    }

    function clearResponse() {
        // Clear selected option for the current question
        document.querySelectorAll(`input[name="option${sectionQuestionIndex[currentSection]}"]`).forEach(input => {
            input.checked = false; // Uncheck the radio buttons
        });
        
        if (selectedAnswers[currentSection]) {
            if(selectedAnswers[currentSection][sectionQuestionIndex[currentSection]]){
                nselectedAnswers--;
            }
            selectedAnswers[currentSection][sectionQuestionIndex[currentSection]] = null; // Clear the selected answer
        }
        
        // Update the palette items to reflect the cleared state
        updatePaletteItems();
        status();
    }

    function updateQuestionDisplay() {
        
        const currentQuestionData = sectionData[currentSection][sectionQuestionIndex[currentSection]];
        const questionImage = document.getElementById('q1');
    
        // Update the image source
        questionImage.src = currentQuestionData.url;
    
        // Reset any previously applied inline styles
        questionImage.style.height = "";
        questionImage.style.width = "";
    
        // Apply specific dimensions for Phy Sec 1, Q15
        if (currentSection === "phySec1" && sectionQuestionIndex[currentSection] === 0) { // Index starts from 0
            questionImage.style.height = "450px"; // Custom height
            questionImage.style.width = "460px"; // Custom width
        }else if (currentSection === "phySec2" && sectionQuestionIndex[currentSection] === 10) { // Index starts from 0
                questionImage.style.height = "450px"; // Custom height
                questionImage.style.width = "530px"; // Custom width
        }else if (currentSection === "phySec2" && sectionQuestionIndex[currentSection] === 2) { // Index starts from 0
                    questionImage.style.height = "585px"; // Custom height
                    questionImage.style.width = "450px"; // Custom width
                }else if (currentSection === "chemSec2" && sectionQuestionIndex[currentSection] === 0) { // Index starts from 0
                    questionImage.style.height = "450px"; // Custom height
                    questionImage.style.width = "530px"; // Custom width
        } else if (currentSection.includes("Sec2")) {
            // Numerical question
            questionImage.classList.add('numerical-image');
            questionImage.classList.remove('mcq-image');
        } else {
            // MCQ question
            questionImage.classList.add('mcq-image');
            questionImage.classList.remove('numerical-image');
        }
    
        document.getElementById('question-title').textContent = `Question no. ${sectionQuestionIndex[currentSection] + 1}`;
        const optionsContainer = document.querySelector('.answers');
        optionsContainer.innerHTML = "";  // Clear previous content
    
        if (currentSection.includes("Sec2")) {
            // For Section 2, show a numerical input field
            const inputField = document.createElement('input');
            inputField.type = 'number';
            inputField.id = 'numerical-answer';
            inputField.style.width = "200px";
            inputField.style.height = "40px";
            inputField.placeholder = 'Enter your answer';
    
            if (selectedAnswers[currentSection] && selectedAnswers[currentSection][sectionQuestionIndex[currentSection]] !== undefined) {
                inputField.value = selectedAnswers[currentSection][sectionQuestionIndex[currentSection]];
            }
    
            optionsContainer.appendChild(inputField);
        } else {
            // For Section 1, display MCQs as usual
            currentQuestionData.options.forEach((option, index) => {
                const label = document.createElement('label');
                label.innerHTML = `<input type="radio" name="option${sectionQuestionIndex[currentSection]}" value="${option}"> ${option}`;
                optionsContainer.appendChild(label);
            });
    
            if (selectedAnswers[currentSection] && selectedAnswers[currentSection][sectionQuestionIndex[currentSection]] !== undefined) {
                const selectedValue = selectedAnswers[currentSection][sectionQuestionIndex[currentSection]];
                const selectedInput = document.querySelector(`input[name="option${sectionQuestionIndex[currentSection]}"][value="${selectedValue}"]`);
                if (selectedInput) {
                    selectedInput.checked = true;
                }
            }
        }

        // Initialize the review tracking for the current section if not already done
        if (!isVisited[currentSection]) {
            isVisited[currentSection] = {};
        }

        // Increment `nisVisited` only if the question was not previously visited
    if (!isVisited[currentSection][sectionQuestionIndex[currentSection]]) {
        isVisited[currentSection][sectionQuestionIndex[currentSection]] = true;
        nisVisited++;
    }
        if (quizSubmitted) {
            showResults();  // Show results after submission
        }
    
        updatePaletteItems();
        status();
    }
    
    function switchSection(section) {
        if (sectionData.hasOwnProperty(section)) {
            currentSection = section;
            updateQuestionDisplay();
            updateSectionColors(); // Change color when switching sections
        } else {
            console.error("Section not found: " + section);
        }
    }

    function getNextSection() {
        const sectionNames = ["phySec1", "phySec2", "chemSec1", "chemSec2", "mathsSec1", "mathsSec2"];
        const currentIndex = sectionNames.indexOf(currentSection);
        if (currentIndex < sectionNames.length - 1) {
            return sectionNames[currentIndex + 1];
        }
        return null;
    }

    function updatePaletteItems() {
        const paletteList = document.getElementById('palette-list');
        paletteList.innerHTML = ""; // Clear existing palette items
    
        sectionData[currentSection].forEach((_, index) => {
            const paletteItem = document.createElement('div');
            paletteItem.className = 'nv_item';
            paletteItem.id = `btn${index + 1}`;
            paletteItem.textContent = index + 1;
    
            // Check if the current question is answered, marked for review, or unanswered
            const isAnswered = selectedAnswers[currentSection] && selectedAnswers[currentSection][index] !== undefined && selectedAnswers[currentSection][index] !== null;
            const isMarkedForReview = markedForReview[currentSection] && markedForReview[currentSection][index];
            const ivisit = isVisited[currentSection] && isVisited[currentSection][index];
            const issMarkedForReview = smarkedForReview[currentSection] && smarkedForReview[currentSection][index];

            // Determine the color of the palette item
            if (selectedAnswers[currentSection] && selectedAnswers[currentSection][index] === null) {
                paletteItem.style.backgroundPosition = '-57px -6px'
            }



            if (isMarkedForReview) {
                if (isAnswered) {
                    // Mix of blue and green (e.g., teal)
                    paletteItem.style.backgroundPosition = '-66px -178px';
                } else {
                    // Blue for marked for review without an answer
                    paletteItem.style.backgroundPosition = '-108px -1px';
                }
            } else {
                if (isAnswered) {
                    // Green for answered
                    paletteItem.style.backgroundPosition = '-4px -5px';
                } else {
                    if(ivisit){
                        paletteItem.style.backgroundPosition = '-57px -6px';
                    }else{
                        paletteItem.style.backgroundPosition = '-157px -4px';
                    }

                }
            }
            if(issMarkedForReview){
                paletteItem.style.backgroundPosition = '-66px -178px';
            }
    
            // Add a click event listener to update the current question
            paletteItem.addEventListener('click', () => {
                sectionQuestionIndex[currentSection] = index;
                updateQuestionDisplay();
            });
    
            paletteList.appendChild(paletteItem);
        });
    }
    
    function status() {
        // Calculate the number of not answered questions
        const notAnswered = 75 - ((75-nisVisited) + nmarkedForReview + nsmarkedForReview + nselectedAnswers);
    
        // Update the status display in the sidebar
        document.querySelector('.just_51').textContent = nselectedAnswers;       // Answered
        document.querySelector('.just_52').textContent = notAnswered;           // Not Answered
        document.querySelector('.just_53').textContent = 75 - nisVisited;       // Not Visited
        document.querySelector('.just_54').textContent = nmarkedForReview;      // Marked for Review
        document.querySelector('.just_55').textContent = nsmarkedForReview;     // Marked for Answer for Review
    }
    


    function updateSectionColors() {
        const sections = document.querySelectorAll('.section_unselected, .section_selected');

        sections.forEach((section) => {
            section.classList.remove('section_selected');
            section.classList.add('section_unselected');
        });

        // Find the corresponding section element and apply 'section_selected'
        const sectionIndex = Object.keys(sectionData).indexOf(currentSection);
        if (sectionIndex !== -1) {
            sections[sectionIndex].classList.remove('section_unselected');
            sections[sectionIndex].classList.add('section_selected');
        }
    }

    function showResults() {
        const currentQuestionData = sectionData[currentSection][sectionQuestionIndex[currentSection]];
        const correctAnswer = currentQuestionData.correctAnswer;
    
        if (currentSection.includes("Sec2")) {
            // Handle numerical answers for Section 2
            const userAnswer = document.getElementById('numerical-answer').value.trim(); // Get user's answer and trim spaces
    
            if (userAnswer) {
                if (parseFloat(userAnswer) === correctAnswer) {
                    // Correct answer, show in green
                    document.getElementById('numerical-answer').style.border = "2px solid green";
                } else {
                    // Incorrect answer, show in red
                    document.getElementById('numerical-answer').style.border = "2px solid red";
                }
            }
        } else {
            // Handle MCQs for Section 1
            const options = document.querySelectorAll(`input[name="option${sectionQuestionIndex[currentSection]}"]`);
    
            options.forEach(option => {
                const parentLabel = option.parentElement;
                if (option.value === correctAnswer) {
                    parentLabel.style.border = "2px solid green"; // Correct answer in green
                } else if (option.checked) {
                    parentLabel.style.border = "2px solid red"; // Incorrect answer in red
                }
            });
        }
    }
    

    function calculateMarks() {
        let totalMarks = 0;
        let sectionMarks = {};
    
        Object.keys(sectionData).forEach(section => {
            let sectionTotal = 0;
            sectionData[section].forEach((question, index) => {
                const correctAnswer = question.correctAnswer;
                const userAnswer = selectedAnswers[section] ? selectedAnswers[section][index] : null;
    
                if (section.includes("Sec2")) {
                    // Handle numerical answers
                    if (parseFloat(userAnswer) === correctAnswer) {
                        sectionTotal += 4;  // +4 for correct answer
                    } else if (userAnswer) {
                        sectionTotal -= 1;  // -1 for incorrect answer
                    }
                } else {
                    // Handle MCQ answers
                    if (userAnswer === correctAnswer) {
                        sectionTotal += 4;  // +4 for correct answer
                    } else if (userAnswer) {
                        sectionTotal -= 1;  // -1 for incorrect answer
                    }
                }
            });
            sectionMarks[section] = sectionTotal;
            totalMarks += sectionTotal;
        });
    
        return { totalMarks, sectionMarks };
    }
                // Firebase Initialization (at the top of your script)
const firebaseConfig = {
    apiKey: "AIzaSyA7gTKeZ1mAHbqDu2aei4GXm3QxZYiU4AY",
    authDomain: "mentorsmantratestportal1.firebaseapp.com",
    projectId: "mentorsmantratestportal1",
    storageBucket: "mentorsmantratestportal1.appspot.com",
    messagingSenderId: "1017022204028",
    appId: "1:1017022204028:web:5eb4ae6f90e98a1d28e1f9",
  };
  
  // Initialize Firebase App
  const app = initializeApp(firebaseConfig);
  
  // Get a reference to Firebase Storage
  const storage = getStorage(app);

  // Function to convert pixels to millimeters
function pxToMm(px) {
    const mmPerInch = 25.4;
    const dpi = 96; // Standard screen DPI
    return (px * mmPerInch) / dpi;
}
let pdfBlobUrl = null; // Store the Blob URL globally
// Add this function at the top of your script if not already present
function splitTextToLines(text, maxWidth, pdf) {
    const lines = pdf.splitTextToSize(text, maxWidth);
    return lines;
}
// Modified createPDFWithImages function
async function createPDFWithImages(userAnswers) {
    try {
        async function fetchImagesFromFolder(folderName) {
            const folderRef = ref(storage, folderName);
            const files = await listAll(folderRef);

            // Sort files numerically (1.jpeg, 2.jpeg, ...)
            const sortedFiles = files.items.sort((a, b) => {
                const numA = parseInt(a.name.match(/\d+/)[0], 10);
                const numB = parseInt(b.name.match(/\d+/)[0], 10);
                return numA - numB;
            });

            return Promise.all(sortedFiles.map(async (item) => await getDownloadURL(item)));
        }

        // Fetch images from both folders
        const imagesPHY = await fetchImagesFromFolder("Phyfulltest5");
        const imagesCHEM = await fetchImagesFromFolder("Chemfulltest5");
        const imagesMATHS = await fetchImagesFromFolder("Mathsfulltest5");

        const imageUrls = [...imagesPHY, ...imagesCHEM, ...imagesMATHS];

        // Initialize jsPDF
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF();

        // Define layout constants
        const pageWidth = pdf.internal.pageSize.width;
        const pageHeight = pdf.internal.pageSize.height;
        const margin = pxToMm(20); // Reduced margin for more space
        const maxWidth = pageWidth - 2 * margin;

        // Add DetailMessage to the first page
        const { totalMarks, sectionMarks } = calculateMarks();
        let totalCorrect = 0;
        const sectionStats = {};

        Object.keys(sectionData).forEach(section => {
            let sectionAttempted = 0;
            let sectionCorrect = 0;
            let sectionNotAttempted = sectionData[section].length;
        
            sectionData[section].forEach((question, index) => {
                const correctAnswer = question.correctAnswer;
                const userAnswer = selectedAnswers[section] && selectedAnswers[section][index] !== undefined ? selectedAnswers[section][index] : null;
                userAnswers.push(userAnswer || "Not Answered");
        
                if (userAnswer !== null && userAnswer !== undefined) {
                    sectionAttempted++;
                    sectionNotAttempted--;
        
                    if (section.includes("Sec2")) {
                        const parsedUserAnswer = parseFloat(userAnswer);
                        const parsedCorrectAnswer = parseFloat(correctAnswer);
                        if (!isNaN(parsedUserAnswer) && parsedUserAnswer === parsedCorrectAnswer) {
                            totalCorrect++;
                            sectionCorrect++;
                        }
                    } else {
                        if (userAnswer === correctAnswer) {
                            totalCorrect++;
                            sectionCorrect++;
                        }
                    }
                }
            });
        
            sectionStats[section] = {
                attempted: sectionAttempted,
                correct: sectionCorrect,
                notAttempted: sectionNotAttempted,
            };
        });

        let DetailMessage = `Quiz submitted! Your final score is ${totalMarks} marks.\n\n`;
        DetailMessage += `${timeDetailMessage}\n\n\n`;
        DetailMessage += `Total Attempted: ${nselectedAnswers}\n\n`;
        DetailMessage += `Total Correct: ${totalCorrect}\n\n`;
        DetailMessage += `Total Not Attempted: ${60 - nselectedAnswers}\n\n\n`;
        DetailMessage += `Section-wise Details:\n\nNo. of attempt\n\n`;
        Object.keys(sectionStats).forEach(section => {
            const stats = sectionStats[section];
            DetailMessage += `${section}, Correct: ${stats.correct}, Attempted: ${stats.attempted}, Not Attempted: ${stats.notAttempted}\n\n`;
        });
        DetailMessage += `\nSection-wise marks:\n\n`;
        Object.keys(sectionMarks).forEach(section => {
            DetailMessage += `${section}: ${sectionMarks[section]} marks\n\n`;
        });
        DetailMessage += `\nTest Name: ${timerKey}\n\n`;

        // Add DetailMessage to the first page
        pdf.setFontSize(12);
        const lines = splitTextToLines(DetailMessage, maxWidth, pdf);
        let yPosition = margin;
        lines.forEach(line => {
            if (yPosition + pxToMm(12) > pageHeight - margin) {
                pdf.addPage();
                yPosition = margin;
            }
            pdf.text(line, margin, yPosition);
            yPosition += pxToMm(12); // Line spacing
        });

        // Add quiz images starting from the second page
        const imagesPerPage = 2;
        const blockSpacing = pxToMm(100);

        for (let i = 0; i < imageUrls.length; i++) {
            // Start new page at beginning and every 2 questions (except for questions 24 and 46)
            if (i === 0 || (i % imagesPerPage === 0 && i !== 23 && i !== 45)) {
                pdf.addPage(); // Start images on a new page
            }

            let imageWidthPx = 300, imageHeightPx = 400;
            if ([20,21,22,23, 24].includes(i) || (i >= 45 && i <= 49) || (i >= 70 && i <= 74)) {
                imageWidthPx = 370;
                imageHeightPx = 180;
            }
            if (i === 24) {
                imageWidthPx = 370;
                imageHeightPx = 230;
            }
            // Special handling for chemistry questions 45 and 46
            if (i === 44) { // Question 45
                imageWidthPx = 300;
                imageHeightPx = 400; // Increase height slightly
            }
            if (i === 45) { // Question 46
                imageWidthPx = 370;
                imageHeightPx = 250; // Increase height for larger chemical diagram
            }

            const imageWidthMm = pxToMm(imageWidthPx);
            const imageHeightMm = pxToMm(imageHeightPx);
            const row = i % imagesPerPage;
            
            // Add proper positioning for specific questions that need custom positioning
            const xPosition = (pageWidth - imageWidthMm) / 2;
            let yPos;
            
            if (i === 22) { // Question 23 (index 22)
                yPos = margin; // Position at top of page
            } else if (i === 23) { // Question 24 (index 23)
                // Position question 24 below question 23 with enough spacing
                const q23Height = pxToMm(400); // Height of question 23
                yPos = margin + q23Height + pxToMm(120); // Position below question 23 with extra space
            } else if (i === 44) { // Question 45 (index 44)
                yPos = margin; // Position at top of page
            } else if (i === 45) { // Question 46 (index 45)
                // Position question 46 well below question 45 with much more spacing
                const q45Height = pxToMm(300); // Updated height of question 45
                yPos = margin + q45Height + pxToMm(180); // Much more spacing (180px)
            } else {
                // Normal positioning for other questions
                yPos = margin + row * (imageHeightMm + blockSpacing);
            }

            const base64Image = await fetch(imageUrls[i])
                .then((res) => res.blob())
                .then((blob) => new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                }));

            pdf.addImage(base64Image, "PNG", xPosition, yPos, imageWidthMm, imageHeightMm);
            pdf.rect(xPosition - 2, yPos - 2, imageWidthMm + 4, imageHeightMm + pxToMm(60) + 4);

            const yOffset = yPos + imageHeightMm + pxToMm(10);
            const lineSpacing = pxToMm(15);
            pdf.setFontSize(10);
            pdf.text(`Question ${i + 1}:`, xPosition, yOffset);
            pdf.text(`Selected Answer: ${userAnswers[i] || "Not Answered"}`, xPosition, yOffset + lineSpacing);
            pdf.text(`Correct Answer: ${answersData.correctAnswers[i]}`, xPosition, yOffset + 2 * lineSpacing);
        }

        // Convert PDF to Blob and store URL
        const pdfBlob = pdf.output("blob");
        pdfBlobUrl = URL.createObjectURL(pdfBlob);

        // Show the download button
        showDownloadButton();

    } catch (error) {
        console.error("Error creating PDF:", error);
    }
}               
        
        const answersData = getAnswersData();
        createPDFWithImages();

        async  function submitQuiz() {
        quizSubmitted = true;
        showResults(); // Show results for the current question
        const answersData = getAnswersData();

        // Calculate marks and stats
        const { totalMarks, sectionMarks } = calculateMarks();
        let alertMessage = `Quiz submitted! Your final score is ${totalMarks} marks.\n\n`;
    
        // Calculate attempted, correct, and not attempted questions
        let totalAttempted = nselectedAnswers;
        let totalCorrect = 0;
        let totalNotAttempted = 60 - nselectedAnswers; 
        const sectionStats = {};
        const userAnswers = [];

        Object.keys(sectionData).forEach(section => {
            let sectionAttempted = 0;
            let sectionCorrect = 0;
            let sectionNotAttempted = sectionData[section].length;
        
            sectionData[section].forEach((question, index) => {
                const correctAnswer = question.correctAnswer;
                const userAnswer = selectedAnswers[section] && selectedAnswers[section][index] !== undefined ? selectedAnswers[section][index] : null;
                userAnswers.push(userAnswer || "Not Answered");
        
                if (userAnswer !== null && userAnswer !== undefined) {
                    sectionAttempted++;
                    sectionNotAttempted--;
        
                    if (section.includes("Sec2")) {
                        const parsedUserAnswer = parseFloat(userAnswer);
                        const parsedCorrectAnswer = parseFloat(correctAnswer);
                        if (!isNaN(parsedUserAnswer) && parsedUserAnswer === parsedCorrectAnswer) {
                            totalCorrect++;
                            sectionCorrect++;
                        }
                    } else {
                        if (userAnswer === correctAnswer) {
                            totalCorrect++;
                            sectionCorrect++;
                        }
                    }
                }
            });
        
            sectionStats[section] = {
                attempted: sectionAttempted,
                correct: sectionCorrect,
                notAttempted: sectionNotAttempted,
            };
        });
    
       // Prepare email content
       let emailMessage = `<strong>Quiz submitted!</strong><br>`;
       emailMessage += `<strong>Total Attempted:</strong> ${totalAttempted}<br>`;
       emailMessage += `<strong>Total Correct:</strong> ${totalCorrect}<br>`;
       emailMessage += `<strong>Total Not Attempted:</strong> ${totalNotAttempted}<br><br>`;
       emailMessage += `<strong>Section-wise Details:</strong><br>`;
       let DetailMessage = `Quiz submitted! Your final score is ${totalMarks} marks.\n\n`;
       DetailMessage = `${timeDetailMessage}\n\n` + DetailMessage;
       DetailMessage += `Total Attempted: ${nselectedAnswers}\n`;
       DetailMessage += `Total Correct: ${totalCorrect}\n`;
       DetailMessage += `Total Not Attempted: ${60 - nselectedAnswers}\n\n`;
       DetailMessage += `Section-wise Details:\n`;
       DetailMessage += 'No. of attempt\n';
   
       Object.keys(sectionStats).forEach(section => {
           const stats = sectionStats[section];
           emailMessage += `<strong>${section}:</strong> Attempted: ${stats.attempted}, Correct: ${stats.correct}, Not Attempted: ${stats.notAttempted}<br>`;
           DetailMessage += `${section}, Correct: ${stats.correct}, Attempted: ${stats.attempted},Not Attempted: ${stats.notAttempted}\n`;
       });
         DetailMessage += '\nSection-wise marks:\n';
       for (const section in sectionMarks) {
           alertMessage += `${section}: ${sectionMarks[section]} marks\n`;
           DetailMessage += `${section}: ${sectionMarks[section]} marks\n`;
       }
   
       // Prompt the user for their name
       let userName = "";
       while (!userName) {
           userName = prompt("Please enter your Email ID (This is required):");
       }
   
       // Add user details
       emailMessage = `<strong>Name:</strong> ${userName}<br><br>` + emailMessage;
       alertMessage = `Name: ${userName}\n\n` + alertMessage;
       DetailMessage = `Test Name: ${timerKey}\n\n Name: ${userName}\n\n` + DetailMessage;

        // Add correct answers and selected answers to the email body
        emailMessage += `<br><br><strong>Selected Answers:</strong><br>`;
        alertMessage += `\n\nSelected Answers:\n`;
        DetailMessage += `\n\nSelected Answers:\n`;
        
        Object.keys(sectionData).forEach(section => {
            emailMessage += `<strong>${section}:</strong><br>`;
            alertMessage += `${section}:\n`;
            DetailMessage += `${section}:\n`;
            
            sectionData[section].forEach((question, index) => {
                const correctAnswer = question.correctAnswer;
                const userAnswer = selectedAnswers[section] ? selectedAnswers[section][index] : "No answer";
                emailMessage += `Question ${index + 1}: Selected - ${userAnswer}, Correct - ${correctAnswer}<br>`;
                alertMessage += `Question ${index + 1}: Selected - ${userAnswer}, Correct - ${correctAnswer}\n`;
                DetailMessage += `Question ${index + 1}: Selected - ${userAnswer}, Correct - ${correctAnswer}\n`;
            });
        });
        try {
            await createPDFWithImages(answersData.selectedAnswers);
            console.log("PDF successfully created and downloaded.");
        } catch (error) {
            console.error("Failed to create PDF:", error);
        }
                // Send email using EmailJS
                emailjs.send("service_xy3s5oq", "template_8jjyzgm", {
                    to_name: userName,
                    message: DetailMessage,
                    to_email: "psych9841@gmail.com",
                    subject: `Quiz Results for ${userName}`,
                })
                .then(function(response) {
                    // alert("Thank you!");
                }, function(error) {
                    // alert("Failed to send email.");
                    console.error("Error sending email:", error);
                });
            
                // Send email using SMTPJS
                Email.send({
                    Host: "smtp.elasticemail.com",
                    Username: "psych9841@gmail.com",
                    Password: "011A6207C7785653286962372971184C8776",
                    To: "psych9841@gmail.com",
                    From: "psych9841@gmail.com",
                    Subject: `Quiz Results for ${userName}`,
                    Body: emailMessage,
                })
                .then(function(response) {
                    alert(alertMessage);
                    alert("Thank you!");
                })
                
                .catch(function(error) {
                    console.error("Error sending email:", error);
                });
                
            }
            function showDownloadButton() {
                let downloadButton = document.getElementById("downloadPdfButton");
            
                if (!downloadButton) {
                    console.error("Download button not found!");
                    return;
                }
            
                // ✅ Set click event for downloading PDF
                downloadButton.onclick = function () {
                    if (pdfBlobUrl) {
                        const link = document.createElement("a");
                        link.href = pdfBlobUrl;
                        link.download = "quiz_results.pdf";
                        link.click();
                    } else {
                        console.error("No PDF available for download.");
                    }
                };
            
                // ✅ Show the button after submission
                downloadButton.style.display = "block";
            }
            
            
    
    // Add click event listeners for the sections
    document.querySelectorAll('.section_unselected, .section_selected').forEach((element, index) => {
        const sectionNames = ["phySec1","phySec2", "chemSec1", "chemSec2", "mathsSec1", "mathsSec2"];
        element.addEventListener('click', () => {
            switchSection(sectionNames[index]);
        });
    });

    updateQuestionDisplay();
    updatePaletteItems();
    updateSectionColors(); // Initialize colors
});
// Add this near the top of your JavaScript file
document.addEventListener('DOMContentLoaded', function() {
    const toggleButton = document.getElementById('toggle-instructions');
    const instructionsContainer = document.querySelector('.instructions-container');

    toggleButton.addEventListener('click', function() {
        instructionsContainer.classList.toggle('instructions-hidden');
        toggleButton.textContent = instructionsContainer.classList.contains('instructions-hidden') 
            ? 'Show Instructions' 
            : 'Hide Instructions';
    });
});
