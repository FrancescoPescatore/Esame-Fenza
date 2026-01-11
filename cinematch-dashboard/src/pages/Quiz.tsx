import { useState, useEffect } from 'react';
import './Quiz.css';

// Mock quiz data - da sostituire con dati dal backend
const mockQuizData = [
    {
        id: 1,
        question: "Which film features a bathhouse for spirits?",
        explanation: "Spirited Away (2001) tells the story of Chihiro, a young girl who must work in a magical bathhouse for spirits to save her parents who were transformed into pigs.",
        answers: [
            { id: 'a', text: "Spirited Away", isCorrect: true },
            { id: 'b', text: "My Neighbor Totoro", isCorrect: false },
            { id: 'c', text: "Princess Mononoke", isCorrect: false },
            { id: 'd', text: "Howl's Moving Castle", isCorrect: false }
        ]
    },
    {
        id: 2,
        question: "Who directed 'My Neighbor Totoro'?",
        explanation: "Hayao Miyazaki, co-founder of Studio Ghibli, directed My Neighbor Totoro in 1988. He is considered one of the greatest animation directors of all time.",
        answers: [
            { id: 'a', text: "Isao Takahata", isCorrect: false },
            { id: 'b', text: "Hayao Miyazaki", isCorrect: true },
            { id: 'c', text: "Mamoru Hosoda", isCorrect: false },
            { id: 'd', text: "Makoto Shinkai", isCorrect: false }
        ]
    },
    {
        id: 3,
        question: "What are the black soot spirits called?",
        explanation: "Susuwatari (literally 'soot wanderers') are the small, fuzzy black spirits that appear in Spirited Away and My Neighbor Totoro. They carry star-shaped candy in the bathhouse!",
        answers: [
            { id: 'a', text: "Kodama", isCorrect: false },
            { id: 'b', text: "Susuwatari", isCorrect: true },
            { id: 'c', text: "Tanuki", isCorrect: false },
            { id: 'd', text: "Yokai", isCorrect: false }
        ]
    },
    {
        id: 4,
        question: "What is Kiki's special talent?",
        explanation: "In Kiki's Delivery Service (1989), young witch Kiki can fly on her broom. She uses this ability to start a delivery service in a coastal town.",
        answers: [
            { id: 'a', text: "Talking to animals", isCorrect: false },
            { id: 'b', text: "Making potions", isCorrect: false },
            { id: 'c', text: "Flying on a broom", isCorrect: true },
            { id: 'd', text: "Becoming invisible", isCorrect: false }
        ]
    },
    {
        id: 5,
        question: "Which film is set during World War II?",
        explanation: "Grave of the Fireflies (1988), directed by Isao Takahata, is a deeply moving film about two siblings struggling to survive in Japan during the final months of WWII.",
        answers: [
            { id: 'a', text: "Ponyo", isCorrect: false },
            { id: 'b', text: "Grave of the Fireflies", isCorrect: true },
            { id: 'c', text: "Arrietty", isCorrect: false },
            { id: 'd', text: "Tales from Earthsea", isCorrect: false }
        ]
    }
];

export function Quiz() {
    const [currentQuestion, setCurrentQuestion] = useState(0);
    const [score, setScore] = useState(0);
    const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
    const [showResult, setShowResult] = useState(false);
    const [isAnswered, setIsAnswered] = useState(false);
    const [quizComplete, setQuizComplete] = useState(false);

    const question = mockQuizData[currentQuestion];

    useEffect(() => {
        setSelectedAnswer(null);
        setShowResult(false);
        setIsAnswered(false);
    }, [currentQuestion]);

    const handleAnswerClick = (answerId: string, isCorrect: boolean) => {
        if (isAnswered) return;

        setSelectedAnswer(answerId);
        setIsAnswered(true);
        setShowResult(true);

        if (isCorrect) {
            setScore(score + 1);
        }
    };

    const goNext = () => {
        if (currentQuestion < mockQuizData.length - 1) {
            setCurrentQuestion(currentQuestion + 1);
        } else {
            setQuizComplete(true);
        }
    };

    const goPrevious = () => {
        if (currentQuestion > 0) {
            setCurrentQuestion(currentQuestion - 1);
        }
    };

    const resetQuiz = () => {
        setCurrentQuestion(0);
        setScore(0);
        setSelectedAnswer(null);
        setShowResult(false);
        setIsAnswered(false);
        setQuizComplete(false);
    };

    const getButtonClass = (answer: { id: string; isCorrect: boolean }) => {
        if (!showResult) return '';
        if (answer.id === selectedAnswer) {
            return answer.isCorrect ? 'correct' : 'incorrect';
        }
        if (answer.isCorrect) return 'correct';
        return 'dimmed';
    };

    // Quiz Complete Screen
    if (quizComplete) {
        const percentage = Math.round((score / mockQuizData.length) * 100);
        let message = '';

        if (percentage === 100) {
            message = "Perfect! You're a true Ghibli expert!";
        } else if (percentage >= 80) {
            message = "Great job! Totoro is proud of you!";
        } else if (percentage >= 60) {
            message = "Good work! Keep watching Ghibli films!";
        } else {
            message = "There's still much to discover in the Ghibli world!";
        }

        return (
            <div className="quiz-page">
                {/* Complete Card */}
                <div className="quiz-card complete-card">
                    <h1>Quiz Complete! 🌟</h1>
                    <div className="score-big">{score}/{mockQuizData.length}</div>
                    <p className="message">{message}</p>
                    <button className="restart-btn" onClick={resetQuiz}>
                        🌸 Try Again
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="quiz-page">
            {/* Question Card */}
            <div className="quiz-card">
                {/* Totoro in top-right of box */}
                <img src="/totoro.svg" alt="Totoro" className="totoro-character" />
                <div className="question-label">Question {currentQuestion + 1}:</div>
                <h2 className="question-text">{question.question}</h2>
            </div>

            {/* Answer Grid */}
            <div className="answers-grid">
                {question.answers.map((answer) => (
                    <button
                        key={answer.id}
                        className={`answer-btn ${getButtonClass(answer)}`}
                        onClick={() => handleAnswerClick(answer.id, answer.isCorrect)}
                        disabled={isAnswered}
                    >
                        <span className="answer-text">{answer.text}</span>
                    </button>
                ))}
            </div>

            {/* Explanation Box - shows after answering */}
            {showResult && (
                <div className={`explanation-box ${selectedAnswer && question.answers.find(a => a.id === selectedAnswer)?.isCorrect ? 'correct' : 'incorrect'}`}>
                    <div className="explanation-header">
                        {selectedAnswer && question.answers.find(a => a.id === selectedAnswer)?.isCorrect
                            ? '✨ Correct!'
                            : '💫 Not quite!'}
                    </div>
                    <p className="explanation-text">{question.explanation}</p>

                    {/* Navigation Buttons */}
                    <div className="nav-buttons">
                        <button
                            className="nav-btn prev-btn"
                            onClick={goPrevious}
                            disabled={currentQuestion === 0}
                        >
                            ← Previous
                        </button>
                        <button
                            className="nav-btn next-btn"
                            onClick={goNext}
                        >
                            {currentQuestion < mockQuizData.length - 1 ? 'Next →' : 'Finish 🌟'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
