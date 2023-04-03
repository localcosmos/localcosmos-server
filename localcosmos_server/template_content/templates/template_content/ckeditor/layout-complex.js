{
    toolbar: [ 'heading', '|', 'bold', 'italic', 'underline', '|', 'link', 'bulletedList', 'numberedList', 'blockQuote', '|', 'insertTable','|', 'sourceEditing' ],
    table: {
        contentToolbar: [
            'tableColumn', 'tableRow', 'mergeTableCells', 'tableProperties', 'tableCellProperties', 'toggleTableCaption'
        ]
    },
	link: {
        decorators: {
            addTargetToExternalLinks: {
                mode: 'manual',
                label: 'Open in a new tab',
                attributes: {
                    target: '_blank',
                    rel: 'noopener noreferrer'
                }
            }
        }
    }
}
