import React, { useState, useEffect } from 'react';

const MENU_ITEMS = [
    { code: '샌', label: '샌드위치', id: '0005' },
    { code: '샐', label: '샐러드', id: '0006' },
    { code: '빵', label: '베이커리', id: '0007' },
    { code: '헬', label: '헬시세트', id: '0009' },
    { code: '닭', label: '닭가슴살', id: '0010' }
];

export default function MenuPreferenceSelector({ value, onChange }) {
    const [items, setItems] = useState([]);

    useEffect(() => {
        // Parse current value (comma separated codes)
        const currentCodes = value ? value.split(',').map(c => c.trim()) : [];
        
        // Create list of items based on current order, adding missing ones at the end
        const orderedItems = [];
        const usedCodes = new Set();

        // Add existing items in order
        currentCodes.forEach(code => {
            const item = MENU_ITEMS.find(i => i.code === code);
            if (item) {
                orderedItems.push(item);
                usedCodes.add(code);
            }
        });

        // Add remaining items
        MENU_ITEMS.forEach(item => {
            if (!usedCodes.has(item.code)) {
                orderedItems.push(item);
            }
        });

        setItems(orderedItems);
    }, [value]);

    const handleDragStart = (e, index) => {
        e.dataTransfer.setData('text/plain', index);
        e.dataTransfer.effectAllowed = 'move';
        // Add a class for styling if needed
        e.target.style.opacity = '0.5';
    };

    const handleDragEnd = (e) => {
        e.target.style.opacity = '1';
    };

    const handleDragOver = (e, index) => {
        e.preventDefault(); // Necessary for allowing drop
        e.dataTransfer.dropEffect = 'move';
    };

    const handleDrop = (e, dropIndex) => {
        e.preventDefault();
        const dragIndex = parseInt(e.dataTransfer.getData('text/plain'), 10);
        if (dragIndex === dropIndex) return;

        const newItems = [...items];
        const [draggedItem] = newItems.splice(dragIndex, 1);
        newItems.splice(dropIndex, 0, draggedItem);

        setItems(newItems);
        
        // Notify parent
        const newValue = newItems.map(i => i.code).join(',');
        onChange(newValue);
    };

    return (
        <div style={{ 
            border: '1px solid #e0e0e0', 
            borderRadius: '8px', 
            overflow: 'hidden',
            background: '#fff'
        }}>
            {items.map((item, index) => (
                <div
                    key={item.code}
                    draggable
                    onDragStart={(e) => handleDragStart(e, index)}
                    onDragEnd={handleDragEnd}
                    onDragOver={(e) => handleDragOver(e, index)}
                    onDrop={(e) => handleDrop(e, index)}
                    style={{
                        padding: '12px 15px',
                        borderBottom: index < items.length - 1 ? '1px solid #f0f0f0' : 'none',
                        display: 'flex',
                        alignItems: 'center',
                        cursor: 'move',
                        background: '#fff',
                        transition: 'background 0.2s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f9f9f9'}
                    onMouseLeave={(e) => e.currentTarget.style.background = '#fff'}
                >
                    <div style={{ 
                        marginRight: '15px', 
                        color: '#999', 
                        fontWeight: 'bold',
                        width: '20px'
                    }}>
                        {index + 1}
                    </div>
                    <div style={{ flex: 1 }}>
                        <span style={{ fontWeight: 600, marginRight: '8px' }}>{item.code}</span>
                        <span style={{ color: '#666', fontSize: '14px' }}>{item.label}</span>
                    </div>
                    <div style={{ color: '#ccc' }}>
                        ☰
                    </div>
                </div>
            ))}
        </div>
    );
}
