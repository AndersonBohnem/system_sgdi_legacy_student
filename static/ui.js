document.addEventListener("DOMContentLoaded", () => {
    const modules = document.querySelectorAll("[data-demand-module]");
    modules.forEach(setupDemandModule);
});

function setupDemandModule(module) {
    const list = module.querySelector("[data-demand-list]");
    if (!list) {
        return;
    }

    const cards = Array.from(list.querySelectorAll("[data-demand-card]"));
    if (!cards.length) {
        return;
    }

    const filterButtons = Array.from(module.querySelectorAll("[data-priority-filter]"));
    const sortControl = module.querySelector("[data-sort-control]");
    const loadMoreArea = module.querySelector("[data-load-more-area]");
    const loadMoreButton = module.querySelector("[data-load-more]");
    const loadMoreStatus = module.querySelector("[data-load-more-status]");
    const emptyState = module.querySelector("[data-empty-state]");
    const searchForm = document.querySelector("[data-search-form]");

    const summary = {
        total: document.querySelector("[data-summary-total]"),
        high: document.querySelector("[data-summary-high]"),
        alerts: document.querySelector("[data-summary-alerts]"),
        view: document.querySelector("[data-summary-view]"),
        order: document.querySelector("[data-summary-order]"),
    };

    const priorityLabels = {
        "": "Todas as prioridades",
        alta: "Alta",
        media: "M\u00e9dia",
        baixa: "Baixa",
    };

    const priorityQueryLabels = {
        alta: "Alta",
        media: "M\u00e9dia",
        baixa: "Baixa",
    };

    const orderLabels = {
        prioridade: "Prioridade primeiro",
        recentes: "Mais recentes primeiro",
    };

    const prioritySlugByLabel = {
        alta: "alta",
        "média": "media",
        media: "media",
        baixa: "baixa",
    };

    const urlParams = new URLSearchParams(window.location.search);
    const urlPriority = (urlParams.get("prioridade") || "").trim().toLowerCase();
    const urlOrder = (urlParams.get("ordenacao") || "").trim();

    const baseBatchSize = Number.parseInt(list.dataset.batchSize || "6", 10);
    const state = {
        filter: prioritySlugByLabel[urlPriority] || list.dataset.currentFilter || "",
        order: orderLabels[urlOrder] ? urlOrder : list.dataset.currentOrder || "prioridade",
        visibleCount: baseBatchSize,
    };

    filterButtons.forEach((button) => {
        button.addEventListener("click", (event) => {
            event.preventDefault();
            state.filter = button.dataset.priorityFilter || "";
            state.visibleCount = baseBatchSize;
            applyState();
        });
    });

    if (sortControl) {
        sortControl.addEventListener("change", () => {
            state.order = sortControl.value || "prioridade";
            state.visibleCount = baseBatchSize;
            applyState();
        });
    }

    if (loadMoreButton) {
        loadMoreButton.addEventListener("click", () => {
            state.visibleCount += baseBatchSize;
            renderCards(getFilteredCards(), false);
        });
    }

    applyState(true);

    function applyState(skipTransition = false) {
        updateControls();
        syncUrl();
        syncSearchForm();
        const filteredCards = getFilteredCards();
        animateList(() => {
            renderCards(filteredCards, true);
            updateSummary(filteredCards);
        }, skipTransition);
    }

    function updateControls() {
        filterButtons.forEach((button) => {
            const isActive = (button.dataset.priorityFilter || "") === state.filter;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });

        if (sortControl) {
            sortControl.value = state.order;
        }
    }

    function getFilteredCards() {
        return cards
            .filter((card) => {
                if (!state.filter) {
                    return true;
                }

                return card.dataset.priority === state.filter;
            })
            .sort(compareCards);
    }

    function compareCards(firstCard, secondCard) {
        if (state.order === "recentes") {
            return secondCard.dataset.created.localeCompare(firstCard.dataset.created);
        }

        const priorityWeight = {
            alta: 1,
            media: 2,
            baixa: 3,
        };

        const firstWeight = priorityWeight[firstCard.dataset.priority] || 99;
        const secondWeight = priorityWeight[secondCard.dataset.priority] || 99;

        if (firstWeight !== secondWeight) {
            return firstWeight - secondWeight;
        }

        return secondCard.dataset.created.localeCompare(firstCard.dataset.created);
    }

    function renderCards(filteredCards, resetVisible) {
        if (resetVisible) {
            state.visibleCount = baseBatchSize;
        }

        filteredCards.forEach((card) => {
            list.appendChild(card);
        });

        cards.forEach((card) => {
            card.hidden = true;
            card.classList.add("is-hidden");
        });

        filteredCards.forEach((card, index) => {
            const shouldShow = index < state.visibleCount;
            card.hidden = !shouldShow;
            card.classList.toggle("is-hidden", !shouldShow);
        });

        if (emptyState) {
            emptyState.hidden = filteredCards.length !== 0;
        }

        updateLoadMore(filteredCards.length);
    }

    function updateLoadMore(totalVisibleCards) {
        if (!loadMoreArea || !loadMoreButton || !loadMoreStatus) {
            return;
        }

        if (totalVisibleCards === 0) {
            loadMoreArea.hidden = true;
            return;
        }

        const currentlyVisible = Math.min(state.visibleCount, totalVisibleCards);
        const hasMore = totalVisibleCards > currentlyVisible;

        loadMoreArea.hidden = !hasMore && totalVisibleCards <= baseBatchSize;
        loadMoreButton.hidden = !hasMore;
        loadMoreStatus.textContent = `Mostrando ${currentlyVisible} de ${totalVisibleCards} demandas.`;

        if (!hasMore && totalVisibleCards > 0) {
            loadMoreArea.hidden = false;
            loadMoreButton.hidden = true;
        }
    }

    function updateSummary(filteredCards) {
        const totals = filteredCards.reduce(
            (accumulator, card) => {
                accumulator.total += 1;
                if (card.dataset.priority === "alta") {
                    accumulator.high += 1;
                }
                if (card.dataset.alert === "true") {
                    accumulator.alerts += 1;
                }
                return accumulator;
            },
            { total: 0, high: 0, alerts: 0 }
        );

        if (summary.total) {
            summary.total.textContent = String(totals.total);
        }
        if (summary.high) {
            summary.high.textContent = String(totals.high);
        }
        if (summary.alerts) {
            summary.alerts.textContent = String(totals.alerts);
        }
        if (summary.view) {
            summary.view.textContent = priorityLabels[state.filter] || priorityLabels[""];
        }
        if (summary.order) {
            summary.order.textContent = orderLabels[state.order] || orderLabels.prioridade;
        }
    }

    function animateList(callback, skipTransition) {
        if (skipTransition) {
            callback();
            return;
        }

        list.classList.add("is-transitioning");
        window.setTimeout(() => {
            callback();
            requestAnimationFrame(() => {
                list.classList.remove("is-transitioning");
            });
        }, 120);
    }

    function syncUrl() {
        const url = new URL(window.location.href);

        if (state.filter) {
            url.searchParams.set(
                "prioridade",
                priorityQueryLabels[state.filter] || state.filter
            );
        } else {
            url.searchParams.delete("prioridade");
        }

        url.searchParams.set("ordenacao", state.order);
        window.history.replaceState({}, "", url);
    }

    function syncSearchForm() {
        if (!searchForm) {
            return;
        }

        syncHiddenInput(
            searchForm,
            "prioridade",
            state.filter ? priorityQueryLabels[state.filter] || state.filter : ""
        );
        syncHiddenInput(searchForm, "ordenacao", state.order);
    }

    function syncHiddenInput(form, inputName, inputValue) {
        let input = form.querySelector(`input[type="hidden"][name="${inputName}"]`);

        if (!inputValue) {
            if (input) {
                input.remove();
            }
            return;
        }

        if (!input) {
            input = document.createElement("input");
            input.type = "hidden";
            input.name = inputName;
            form.prepend(input);
        }

        input.value = inputValue;
    }
}
