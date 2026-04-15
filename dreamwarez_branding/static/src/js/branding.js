/** @odoo-module **/

function replaceText(node) {
    if (!node) return;

    // Only process TEXT NODES (fast)
    if (node.nodeType === Node.TEXT_NODE) {
        let text = node.nodeValue;

        if (!text || !text.includes("Odoo")) return;

        text = text.replace(/OdooBot Status/g, "Dreamsbot Status");
        text = text.replace(/Odoo/g, "Dreamwarez");

        node.nodeValue = text;
    } else {
        node.childNodes.forEach(replaceText);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // Initial run (lightweight)
    replaceText(document.body);

    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                replaceText(node); // only new nodes
            });
        });
    });

    if (document.body) {
        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });
    }
});






















// /** @odoo-module **/

// function replaceText() {
//     document.querySelectorAll("*").forEach((el) => {
//         if (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3) {
//             if (el.textContent.includes("Odoo")) {
//                 el.textContent = el.textContent.replace(/Odoo/g, "Dreamwarez");
//             }
//         }
//     });
// }

// document.addEventListener("DOMContentLoaded", () => {
//     // Run once
//     replaceText();

//     // Observe future changes
//     const observer = new MutationObserver(() => {
//         replaceText();
//     });

//     if (document.body) {
//         observer.observe(document.body, {
//             childList: true,
//             subtree: true,
//         });
//     }
// });