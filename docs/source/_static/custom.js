document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.toctree-l1 > a.reference.external').forEach(link => {

        link.setAttribute('target', '_blank');


        if (link.textContent.trim() === 'GitHub') {
            const icon = document.createElement('i'); 
            icon.className = 'fa fa-github'; 
            icon.style.color = 'light-gray';
            icon.style.marginLeft = '5px'; 
            link.appendChild(icon); 
        }
    });
});