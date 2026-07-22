from flask import Flask, render_template, request, jsonify
from difflib import get_close_matches
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

books_df = pd.read_csv("Books.csv")
ratings_df = pd.read_csv("Ratings.csv")

rating_name = ratings_df.merge(books_df, on="ISBN")

# Book-Rating == 0 means "read but not explicitly scored" in this dataset,
# not "rated zero out of ten". Mixing those in drags every average down
# hard (e.g. Harry Potter titles were landing near 2/5 instead of ~4.5/5),
# so popularity and similarity are both computed from explicit ratings only.
explicit_ratings = rating_name[rating_name["Book-Rating"] > 0]

num_rating_df = explicit_ratings.groupby("Book-Title")["Book-Rating"].count().reset_index()
num_rating_df.rename(columns={"Book-Rating": "num_ratings"}, inplace=True)

avg_rating_df = explicit_ratings.groupby("Book-Title")["Book-Rating"].mean().reset_index()
avg_rating_df.rename(columns={"Book-Rating": "avg_rating"}, inplace=True)

popularity_df = num_rating_df.merge(avg_rating_df, on="Book-Title")
popular_df = (
    popularity_df[popularity_df["num_ratings"] >= 100]
    .sort_values("avg_rating", ascending=False)
    .head(50)
)

popular_df = popular_df.merge(
    books_df[["Book-Title", "Book-Author", "Image-URL-M", "ISBN"]].drop_duplicates("Book-Title"),
    on="Book-Title",
    how="left",
)
popular_df = popular_df[["Book-Title", "Book-Author", "Image-URL-M", "ISBN", "num_ratings", "avg_rating"]].reset_index(drop=True)

# Build the collaborative filtering matrix. User/book "activity" here is
# based on ALL interactions (including implicit 0-ratings) — a 0 still
# tells us the user picked up and rated that book, which is a useful signal
# for finding similar readers even though it shouldn't count toward a
# book's average score. This matches the pool the notebook trains on.
user_rating_counts = rating_name.groupby("User-ID").count()["Book-Rating"] > 200
active_users = user_rating_counts[user_rating_counts].index
filtered_rating = rating_name[rating_name["User-ID"].isin(active_users)]

book_rating_counts = filtered_rating.groupby("Book-Title").count()["Book-Rating"] >= 50
popular_books = book_rating_counts[book_rating_counts].index
final_ratings = filtered_rating[filtered_rating["Book-Title"].isin(popular_books)]

pt = final_ratings.pivot_table(index="Book-Title", columns="User-ID", values="Book-Rating")
pt = pt.fillna(0)

similarity_scores = cosine_similarity(pt)

# Every title that can actually produce recommendations (used for the
# searchable dropdown so a selection always resolves to a result).
all_book_titles = sorted(str(t) for t in pt.index)

book_lookup = {}
for _, row in books_df.drop_duplicates("Book-Title").iterrows():
    title = str(row["Book-Title"]).strip()
    if title:
        book_lookup[title] = {
            "author": row["Book-Author"],
            "image": row["Image-URL-M"],
            "isbn": row["ISBN"],
        }


def normalize_title(title):
    return "".join(ch.lower() for ch in str(title) if ch.isalnum())


def find_book_match(user_input):
    if not user_input:
        return None

    title = user_input.strip()
    candidates = [str(candidate) for candidate in pt.index]

    # Exact, verbatim match first — guarantees a dropdown selection always
    # resolves to itself, even when a near-duplicate (differing only in
    # punctuation/spacing, e.g. "The Hours: A Novel" vs "The Hours : A
    # Novel") exists elsewhere in the matrix.
    if title in candidates:
        return title

    exact_matches = [candidate for candidate in candidates if normalize_title(candidate) == normalize_title(title)]
    if exact_matches:
        return exact_matches[0]

    contains_matches = [candidate for candidate in candidates if normalize_title(title) in normalize_title(candidate)]
    if contains_matches:
        return contains_matches[0]

    close_matches = get_close_matches(title, candidates, n=1, cutoff=0.35)
    return close_matches[0] if close_matches else None


def get_recommendations(user_input):
    if not user_input or not user_input.strip():
        return None, "Please enter or pick a book title.", None

    matched_title = find_book_match(user_input)
    if matched_title is None:
        return None, "No matching book title found. Please try another title.", None

    index = list(pt.index).index(matched_title)
    similar_items = sorted(list(enumerate(similarity_scores[index])), key=lambda x: x[1], reverse=True)[1:6]

    data = []
    for item_index, _ in similar_items:
        rec_title = pt.index[item_index]
        meta = book_lookup.get(rec_title, {})
        data.append({
            "title": rec_title,
            "author": meta.get("author", "Unknown Author"),
            "image": meta.get("image", ""),
            "isbn": meta.get("isbn", ""),
        })

    return data, None, matched_title


@app.route("/")
def index():
    return render_template(
        "index.html",
        book_name=list(popular_df["Book-Title"].values),
        author=list(popular_df["Book-Author"].values),
        image=list(popular_df["Image-URL-M"].values),
        isbn=list(popular_df["ISBN"].values),
        votes=list(popular_df["num_ratings"].values),
        rating=list(popular_df["avg_rating"].values),
        all_books=all_book_titles,
    )


@app.route("/recommend")
def recommend_ui():
    return render_template("recommend.html", data=None, error=None, user_input="", matched_title=None, all_books=all_book_titles)


@app.route("/recommend_books", methods=["POST"])
def recommend():
    user_input = request.form.get("user_input", "")
    data, error, matched_title = get_recommendations(user_input)
    return render_template(
        "recommend.html",
        data=data,
        error=error,
        user_input=user_input,
        matched_title=matched_title,
        all_books=all_book_titles,
    )


@app.route("/api/books")
def api_books():
    return jsonify(all_book_titles)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
