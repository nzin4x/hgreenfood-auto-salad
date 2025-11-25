import React, { useState, useEffect } from 'react';

export default function ExclusionCalendar({ userId, initialDates = [], onSave }) {
    const [selectedDates, setSelectedDates] = useState(initialDates);
    const [currentMonth, setCurrentMonth] = useState(new Date());

    useEffect(() => {
        setSelectedDates(initialDates);
    }, [initialDates]);

    const getDaysInMonth = (date) => {
        const year = date.getFullYear();
        const month = date.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const days = [];

        // Add empty cells for days before month starts
        for (let i = 0; i < firstDay.getDay(); i++) {
            days.push(null);
        }

        // Add all days in month
        for (let day = 1; day <= lastDay.getDate(); day++) {
            days.push(new Date(year, month, day));
        }

        return days;
    };

    const formatDate = (date) => {
        if (!date) return '';
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };

    const toggleDate = (date) => {
        const dateStr = formatDate(date);
        if (selectedDates.includes(dateStr)) {
            setSelectedDates(selectedDates.filter(d => d !== dateStr));
        } else {
            setSelectedDates([...selectedDates, dateStr]);
        }
    };

    const isSelected = (date) => {
        if (!date) return false;
        return selectedDates.includes(formatDate(date));
    };

    const isPast = (date) => {
        if (!date) return false;
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return date < today;
    };

    const changeMonth = (delta) => {
        const newDate = new Date(currentMonth);
        newDate.setMonth(newDate.getMonth() + delta);
        setCurrentMonth(newDate);
    };

    const handleSave = () => {
        onSave(selectedDates);
    };

    const days = getDaysInMonth(currentMonth);
    const monthName = currentMonth.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long' });

    return (
        <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ marginTop: 0, marginBottom: '15px' }}>자동예약 제외 날짜 선택</h4>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <button 
                    onClick={() => changeMonth(-1)}
                    style={{ 
                        padding: '5px 10px', 
                        background: '#667eea', 
                        color: 'white', 
                        border: 'none', 
                        borderRadius: '4px',
                        cursor: 'pointer'
                    }}
                >
                    ◀
                </button>
                <span style={{ fontWeight: 600 }}>{monthName}</span>
                <button 
                    onClick={() => changeMonth(1)}
                    style={{ 
                        padding: '5px 10px', 
                        background: '#667eea', 
                        color: 'white', 
                        border: 'none', 
                        borderRadius: '4px',
                        cursor: 'pointer'
                    }}
                >
                    ▶
                </button>
            </div>

            <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(7, 1fr)', 
                gap: '5px',
                marginBottom: '15px'
            }}>
                {['일', '월', '화', '수', '목', '금', '토'].map(day => (
                    <div key={day} style={{ 
                        textAlign: 'center', 
                        fontWeight: 600, 
                        fontSize: '12px',
                        color: '#666',
                        padding: '5px'
                    }}>
                        {day}
                    </div>
                ))}
                
                {days.map((date, index) => (
                    <div
                        key={index}
                        onClick={() => date && !isPast(date) && toggleDate(date)}
                        style={{
                            padding: '10px',
                            textAlign: 'center',
                            borderRadius: '4px',
                            cursor: date && !isPast(date) ? 'pointer' : 'default',
                            background: date ? (isSelected(date) ? '#667eea' : '#fff') : 'transparent',
                            color: date ? (isSelected(date) ? 'white' : (isPast(date) ? '#ccc' : '#333')) : 'transparent',
                            border: date ? '1px solid #ddd' : 'none',
                            opacity: isPast(date) ? 0.5 : 1,
                            fontSize: '14px'
                        }}
                    >
                        {date ? date.getDate() : ''}
                    </div>
                ))}
            </div>

            <div style={{ marginBottom: '10px', fontSize: '12px', color: '#666' }}>
                선택된 날짜: {selectedDates.length}개
            </div>

            <button
                onClick={handleSave}
                style={{
                    width: '100%',
                    padding: '10px',
                    background: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: 600
                }}
            >
                저장
            </button>
        </div>
    );
}
