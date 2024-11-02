document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/comments')
        .then(response => response.json())
        .then(comments => {
            comments.forEach(comment => {
                displayComment(comment, false);
                comment.replies.forEach(reply => {
                    displayComment(reply, true);
                });
            });
        })
        .catch(error => {
            console.error('Error al cargar los comentarios:', error);
        });
});

document.getElementById('comment-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const comment = document.getElementById('comment').value;
    const media = document.getElementById('media').files[0];
    const parent_id = document.getElementById('parent_id').value;

    const formData = new FormData();
    formData.append('comment', comment);
    formData.append('parent_id', parent_id);
    if (media) {
        formData.append('media', media);
    }

    fetch('/api/comments', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayComment(data.comment, !!parent_id); // Indicar si es respuesta
            resetFileInput();
            document.getElementById('parent_id').value = '';
        } else {
            alert('Hubo un problema al enviar tu comentario.');
        }
    })
    .catch(error => {
        console.error('Error en la solicitud:', error);
        alert('Hubo un problema al conectar con el servidor.');
    });
});

document.getElementById('media').addEventListener('change', function() {
    const fileName = this.files[0] ? this.files[0].name : 'Ningún archivo seleccionado';
    document.getElementById('file-name').textContent = fileName;
    document.getElementById('discard-file').style.display = this.files[0] ? 'inline-block' : 'none';
});

document.getElementById('discard-file').addEventListener('click', function() {
    resetFileInput();
});

function resetFileInput() {
    const mediaInput = document.getElementById('media');
    mediaInput.value = '';
    document.getElementById('file-name').textContent = 'Ningún archivo seleccionado';
    document.getElementById('discard-file').style.display = 'none';
}

function displayComment(comment, isReply = false) {
    const commentsDiv = isReply ? document.getElementById(`replies-${comment.parent_id}`) : document.getElementById('comments');
    
    // Crear el div de respuestas si no existe
    if (isReply && !commentsDiv) {
        const parentCommentDiv = document.querySelector(`.comment[data-id="${comment.parent_id}"]`);
        const repliesDiv = document.createElement('div');
        repliesDiv.id = `replies-${comment.parent_id}`;
        repliesDiv.classList.add('replies');
        parentCommentDiv.appendChild(repliesDiv);
    }

    const commentDiv = document.createElement('div');
    commentDiv.classList.add('comment');
    if (isReply) {
        commentDiv.classList.add('reply');  // Agregar clase 'reply' si es una respuesta
    }
    commentDiv.setAttribute('data-id', comment.id);
    commentDiv.innerHTML = `
        <strong>${comment.username}</strong>
        <p id="comment-text-${comment.id}">${comment.text}</p>
        ${comment.media ? (comment.media.endsWith('.mp4') ? `<video src="${comment.media}" controls style="max-width: 100%;"></video>` : `<img src="${comment.media}" alt="Multimedia" style="max-width: 100%;">`) : ''}
        <div class="like-section">
            <button onclick="likeComment('${comment.id}', '${comment.username}')">❤️</button> <span id="like-count-${comment.id}">${comment.likes}</span> likes
        </div>
        <button onclick="replyToComment('${comment.id}')">Responder</button>
        <button onclick="editComment('${comment.id}')">Editar</button>
        <button onclick="deleteComment('${comment.id}')">Eliminar</button>
        <button onclick="reportComment('${comment.id}')">Reportar</button>
        <div id="replies-${comment.id}" class="replies"></div>
    `;
    commentsDiv.appendChild(commentDiv);
}

function likeComment(commentId, username) {
    const likedComments = JSON.parse(localStorage.getItem(`likedComments-${username}`)) || [];
    if (!likedComments.includes(commentId)) {
        fetch(`/api/comments/${commentId}/like`, {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById(`like-count-${commentId}`).textContent = data.likes;
                likedComments.push(commentId);
                localStorage.setItem(`likedComments-${username}`, JSON.stringify(likedComments));
            } else {
                alert('Hubo un problema al dar like.');
            }
        })
        .catch(error => {
            console.error('Error en la solicitud de like:', error);
            alert('Hubo un problema al conectar con el servidor.');
        });
    } else {
        alert('Ya has dado like a este comentario.');
    }
}

function replyToComment(commentId) {
    document.getElementById('parent_id').value = commentId;
    document.getElementById('comment').focus();
}

function editComment(commentId) {
    const commentTextElement = document.getElementById(`comment-text-${commentId}`);
    const currentText = commentTextElement.textContent;
    const newText = prompt('Edita tu comentario:', currentText);
    if (newText && newText !== currentText) {
        const formData = new FormData();
        formData.append('text', newText);

        fetch(`/api/comments/${commentId}`, {
            method: 'PUT',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                commentTextElement.textContent = data.text;
                commentTextElement.closest('.comment').classList.remove('edit-mode');
            } else {
                alert('Hubo un problema al editar el comentario.');
            }
        })
        .catch(error => {
            console.error('Error en la solicitud de edición:', error);
            alert('Hubo un problema al conectar con el servidor.');
        });

        commentTextElement.closest('.comment').classList.add('edit-mode');
    }
}

function deleteComment(commentId) {
    fetch(`/api/comments/${commentId}`, {
        method: 'DELETE',
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.querySelector(`button[onclick="deleteComment('${commentId}')"]`).parentElement.remove();
        } else {
            alert('Hubo un problema al eliminar el comentario.');
        }
    })
    .catch(error => {
        console.error('Error en la solicitud de eliminación:', error);
        alert('Hubo un problema al conectar con el servidor.');
    });
}

function reportComment(commentId) {
    if (confirm('¿Estás seguro de que deseas reportar este comentario?')) {
        fetch(`/api/comments/${commentId}/report`, {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Comentario reportado con éxito. Será revisado por un moderador.');
            } else {
                alert('Hubo un problema al reportar el comentario.');
            }
        })
        .catch(error => {
            console.error('Error en la solicitud de reporte:', error);
            alert('Hubo un problema al conectar con el servidor.');
        });
    }
}
