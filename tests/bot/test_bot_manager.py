from app.store.bot.helpers import MessageHelper, CmdEnum
from tests.fixtures import custom_update


class TestHandleBaseUpdates:

    async def test_handle_start_game(self, store, start_game_update, creator_1):
        """trying start game session"""
        await store.bots_manager.handle_update(update=start_game_update)
        assert store.vk_api.send_message.call_count == 2
        req_message = MessageHelper.started(creator_1.name)
        assert store.vk_api.send_message.mock_calls[0].kwargs["message"] == req_message

    async def test_handle_wrong_start(self, store, start_game_update, creator_1, fill_db_with_questions,
                                      preparing_state):
        """Create 3x3 questions, start game session, then trying start game session again"""
        await store.bots_manager.handle_update(update=start_game_update)
        assert store.vk_api.send_message.call_count == 3
        req_message = MessageHelper.wrong_start
        assert store.vk_api.send_message.mock_calls[2].kwargs["message"] == req_message

    async def test_handle_participate(self, store, start_game_update, participate_update, player_1,
                                      fill_db_with_questions, preparing_state):
        """Create 3x3 questions, start game session, then trying to add player_1 to game session"""
        await store.bots_manager.handle_update(update=participate_update)
        assert store.vk_api.send_message.call_count == 3
        req_message = MessageHelper.new_player_added(player_1.name)
        assert store.vk_api.send_message.mock_calls[2].kwargs["message"] == req_message

    async def test_handle_run_game(self, store, run_game_update, creator_1, fill_db_with_questions, preparing_state):
        """Create 3x3 questions, start game session, then run quiz with one player (creator)"""
        await store.bots_manager.handle_update(update=run_game_update)
        assert store.vk_api.send_message.call_count == 4
        req_message = MessageHelper.start_quiz
        assert store.vk_api.send_message.mock_calls[2].kwargs["message"] == req_message

    async def test_handle_question(self, chat_1, store, run_game_update, question_update, creator_1, player_1,
                                   fill_db_with_questions, waiting_question_state):
        """Create 3x3 questions, start game session, run quiz with one player (creator), and get chosen answer"""
        chat_sessions = await store.game_sessions.list_sessions(id_only=True, chat_id=chat_1.id)
        state = await store.game_sessions.get_session_state_by_id(chat_sessions[0])
        answerer = state.last_answerer
        if answerer == player_1.id:
            answerer = player_1
        else:
            answerer = creator_1
        update = custom_update(peer_id=chat_1.id, from_id=answerer.id, payload_cmd=CmdEnum.QUESTION.value, payload_txt="1")
        await store.bots_manager.handle_update(update=update)
        assert store.vk_api.send_message.call_count == 6
        question_id = int(question_update.object.message.payload_txt)
        question = await store.quizzes.get_question_by_id(question_id)
        req_message_1 = MessageHelper.choose_question(name=answerer.name)
        req_message_2 = MessageHelper.question(question=question.title)
        assert store.vk_api.send_message.mock_calls[4].kwargs["message"] == req_message_1
        assert store.vk_api.send_message.mock_calls[5].kwargs["message"] == req_message_2

    async def test_handle_wrong_answer(self, chat_1, store, run_game_update, question_update, creator_1, player_1,
                                       fill_db_with_questions, waiting_question_state):
        """Create 3x3 questions, start game session, run quiz with two players, and get wrong answer from one player"""

        chat_sessions = await store.game_sessions.list_sessions(id_only=True, chat_id=chat_1.id)
        state = await store.game_sessions.get_session_state_by_id(chat_sessions[0])
        answerer_id = state.last_answerer
        if answerer_id == player_1.id:
            answerer = player_1
        elif answerer_id == creator_1.id:
            answerer = creator_1
        update = custom_update(peer_id=chat_1.id, from_id=answerer.id, payload_cmd=CmdEnum.QUESTION.value,
                               payload_txt="1")
        await store.bots_manager.handle_update(update=update)
        update = custom_update(peer_id=chat_1.id, from_id=player_1.id, payload_cmd=CmdEnum.ANSWER.value,
                               payload_txt=False)
        await store.bots_manager.handle_update(update=update)
        assert store.vk_api.send_message.call_count == 8
        question_id = int(question_update.object.message.payload_txt)
        question = await store.quizzes.get_question_by_id(question_id)
        req_message_1 = MessageHelper.answered_wrong(name=player_1.name, points=-question.points,
                                                     curpoints=-question.points)
        req_message_2 = MessageHelper.question(question=question.title)
        assert store.vk_api.send_message.mock_calls[-2].kwargs["message"] == req_message_1
        assert store.vk_api.send_message.mock_calls[-1].kwargs["message"] == req_message_2

    async def test_handle_all_players_wrong(self, chat_1, store, run_game_update, question_update, creator_1, player_1,
                                            fill_db_with_questions, waiting_question_state):
        """Create 3x3 questions, start game session, run quiz with two players, and get wrong answer from both
        players"""

        chat_sessions = await store.game_sessions.list_sessions(id_only=True, chat_id=chat_1.id)
        state = await store.game_sessions.get_session_state_by_id(chat_sessions[0])
        answerer_id = state.last_answerer
        if answerer_id == player_1.id:
            answerer = player_1
        elif answerer_id == creator_1.id:
            answerer = creator_1
        update = custom_update(peer_id=chat_1.id, from_id=answerer.id, payload_cmd=CmdEnum.QUESTION.value,
                               payload_txt="1")
        await store.bots_manager.handle_update(update=update)
        update = custom_update(peer_id=chat_1.id, from_id=player_1.id, payload_cmd=CmdEnum.ANSWER.value,
                               payload_txt=False)
        await store.bots_manager.handle_update(update=update)
        update = custom_update(peer_id=chat_1.id, from_id=creator_1.id, payload_cmd=CmdEnum.ANSWER.value,
                               payload_txt=False)
        await store.bots_manager.handle_update(update=update)
        assert store.vk_api.send_message.call_count == 11
        question_id = int(question_update.object.message.payload_txt)
        question = await store.quizzes.get_question_by_id(question_id)
        answer = next((a for a in question.answers if a.is_correct), None)
        req_message_1 = MessageHelper.answered_wrong(name=creator_1.name, points=-question.points,
                                                     curpoints=-question.points)
        req_message_2 = MessageHelper.no_players_left(answer=answer.title)
        req_message_3 = MessageHelper.choose_question(name=answerer.name)
        assert store.vk_api.send_message.mock_calls[-3].kwargs["message"] == req_message_1
        assert store.vk_api.send_message.mock_calls[-2].kwargs["message"] == req_message_2
        assert store.vk_api.send_message.mock_calls[-1].kwargs["message"] == req_message_3

    async def test_handle_correct_answer(self, chat_1, store, run_game_update, question_update, creator_1, player_1,
                                         fill_db_with_questions, waiting_question_state):
        """Create 3x3 questions, start game session, run quiz with one player (creator), and get chosen answer"""
        chat_sessions = await store.game_sessions.list_sessions(id_only=True, chat_id=chat_1.id)
        state = await store.game_sessions.get_session_state_by_id(chat_sessions[0])
        answerer_id = state.last_answerer
        if answerer_id == player_1.id:
            answerer = player_1
        elif answerer_id == creator_1.id:
            answerer = creator_1
        update = custom_update(peer_id=chat_1.id, from_id=answerer.id, payload_cmd=CmdEnum.QUESTION.value,
                               payload_txt="1")
        await store.bots_manager.handle_update(update=update)
        update = custom_update(peer_id=chat_1.id, from_id=player_1.id, payload_cmd=CmdEnum.ANSWER.value,
                               payload_txt=True)
        await store.bots_manager.handle_update(update=update)
        assert store.vk_api.send_message.call_count == store.vk_api.send_message.call_count
        question_id = int(question_update.object.message.payload_txt)
        question = await store.quizzes.get_question_by_id(question_id)
        req_message_1 = MessageHelper.answered_correct(name=player_1.name, points=question.points,
                                                       curpoints=question.points)
        req_message_2 = MessageHelper.choose_question(name=player_1.name)

        assert store.vk_api.send_message.mock_calls[-2].kwargs["message"] == req_message_1
        assert store.vk_api.send_message.mock_calls[-1].kwargs["message"] == req_message_2

    async def test_handle_repeating_answerer(self, chat_1, store, run_game_update, question_update, creator_1, player_1,
                                             fill_db_with_questions, waiting_question_state):
        """Create 3x3 questions, start game session, run quiz with two players, one chooses question, some of them
        answers wrong, then tries to answer one more time"""
        chat_sessions = await store.game_sessions.list_sessions(id_only=True, chat_id=chat_1.id)
        state = await store.game_sessions.get_session_state_by_id(chat_sessions[0])
        answerer_id = state.last_answerer
        if answerer_id == player_1.id:
            answerer = player_1
        elif answerer_id == creator_1.id:
            answerer = creator_1
        update = custom_update(peer_id=chat_1.id, from_id=answerer.id, payload_cmd=CmdEnum.QUESTION.value, payload_txt="1")
        await store.bots_manager.handle_update(update=update)
        update = custom_update(peer_id=chat_1.id, from_id=player_1.id, payload_cmd=CmdEnum.ANSWER.value,
                               payload_txt=False)
        await store.bots_manager.handle_update(update=update)
        await store.bots_manager.handle_update(update=update)
        assert store.vk_api.send_message.call_count == 9
        question_id = int(question_update.object.message.payload_txt)
        req_message_2 = MessageHelper.can_not_answer(name=player_1.name)
        assert store.vk_api.send_message.mock_calls[-1].kwargs["message"] == req_message_2

    async def test_show_results_with_no_res(self, chat_1, store, player_1, start_game_update, run_game_update, stop_game_update, creator_1,
                                fill_db_with_questions):
        """Showing results before start"""

        update = custom_update(peer_id=chat_1.id, from_id=player_1.id, payload_cmd=CmdEnum.RESULTS.value,
                               payload_txt=None)
        await store.bots_manager.handle_update(update=update)
        assert store.vk_api.send_message.call_count == 1
        assert store.vk_api.send_message.mock_calls[0].kwargs["message"] == MessageHelper.no_results

    async def test_show_results_on_preparing(self, chat_1, store, player_1, start_game_update, run_game_update,
                                             stop_game_update, creator_1, fill_db_with_questions, preparing_state):
        """Showing results successfully after start"""

        update = custom_update(peer_id=chat_1.id, from_id=player_1.id, payload_cmd=CmdEnum.RESULTS.value,
                               payload_txt=None)
        await store.bots_manager.handle_update(update=update)
        assert store.vk_api.send_message.call_count == 3
        assert store.vk_api.send_message.mock_calls[2].kwargs["message"] == MessageHelper.no_results

    async def test_show_results_waiting_question(self, chat_1, store, player_1, start_game_update, run_game_update,
                                                 stop_game_update, creator_1, fill_db_with_questions,
                                                 waiting_question_state):
        """Showing results successfully while waiting question"""

        update = custom_update(peer_id=chat_1.id, from_id=player_1.id, payload_cmd=CmdEnum.RESULTS.value,
                               payload_txt=None)
        await store.bots_manager.handle_update(update=update)
        assert store.vk_api.send_message.call_count == 6
        results_dict = {creator_1.name: "0", player_1.name: "0"}
        assert store.vk_api.send_message.mock_calls[5].kwargs["message"] == MessageHelper.just_show_results(results_dict)


class TestHandleStopUpdates:
    async def test_stop_no_game(self, store, stop_game_update, creator_1, fill_db_with_questions):
        """Trying to stop game when there is no running session"""

        await store.bots_manager.handle_update(update=stop_game_update)
        assert store.vk_api.send_message.call_count == 1
        assert store.vk_api.send_message.mock_calls[0].kwargs["message"] == MessageHelper.no_session_to_stop

    async def test_stop_preparing_game(self, store, run_game_update, stop_game_update, creator_1,
                                       fill_db_with_questions, preparing_state):
        """Create 3x3 questions, start game session, then trying to stop game out of preparing state"""
        results_dict = {creator_1.name: "0"}
        req_message = MessageHelper.quiz_ended_on_stop(name=creator_1.name, results=results_dict)

        await store.bots_manager.handle_update(update=stop_game_update)
        assert store.vk_api.send_message.call_count == 3
        assert store.vk_api.send_message.mock_calls[2].kwargs["message"] == req_message

    async def test_stop_game_after_add_player(self, store, run_game_update, participate_update, stop_game_update,
                                              creator_1, player_1, fill_db_with_questions, preparing_state):
        """Create 3x3 questions, start game session, add one player, then trying to stop game out of preparing state"""
        results_dict = {creator_1.name: "0", player_1.name: "0"}
        req_message = MessageHelper.quiz_ended_on_stop(name=creator_1.name, results=results_dict)

        await store.bots_manager.handle_update(update=participate_update)
        await store.bots_manager.handle_update(update=stop_game_update)
        assert store.vk_api.send_message.call_count == 4
        assert store.vk_api.send_message.mock_calls[3].kwargs["message"] == req_message

    async def test_stop_waiting_question_game(self, store, stop_game_update, creator_1, fill_db_with_questions,
                                              waiting_question_singleplayer_state):
        """Create 3x3 questions, start game session, run quiz, then trying to stop game out of waiting question state"""
        results_dict = {creator_1.name: "0"}
        req_message = MessageHelper.quiz_ended_on_stop(name=creator_1.name, results=results_dict)

        await store.bots_manager.handle_update(update=stop_game_update)
        assert store.vk_api.send_message.call_count == 5
        assert store.vk_api.send_message.mock_calls[4].kwargs["message"] == req_message

    async def test_stop_waiting_question_several_players(self, store, stop_game_update, creator_1, player_1,
                                                         fill_db_with_questions, waiting_question_state):
        """Create 3x3 questions, start game session, run quiz, then trying to stop game out of waiting question state"""
        results_dict = {creator_1.name: "0", player_1.name: "0"}
        req_message = MessageHelper.quiz_ended_on_stop(name=creator_1.name, results=results_dict)

        await store.bots_manager.handle_update(update=stop_game_update)
        assert store.vk_api.send_message.call_count == 6
        assert store.vk_api.send_message.mock_calls[5].kwargs["message"] == req_message

    async def test_stop_waiting_answer_game(self, store, stop_game_update, creator_1, fill_db_with_questions,
                                            waiting_answer_singleplayer_state):
        """Create 3x3 questions, start game session, run quiz, get chosen question, and then trying to stop game out of
        waiting answer state"""
        results_dict = {creator_1.name: "0"}
        req_message = MessageHelper.quiz_ended_on_stop(name=creator_1.name, results=results_dict)

        await store.bots_manager.handle_update(update=stop_game_update)
        assert store.vk_api.send_message.call_count == 6
        assert store.vk_api.send_message.mock_calls[5].kwargs["message"] == req_message

    async def test_stop_after_wrong_answer(self, store, stop_game_update, creator_1, fill_db_with_questions,
                                           after_wrong_answer_singleplayer_state):
        """Create 3x3 questions, start game session, run quiz, get chosen question, get wrong answer, and then trying
        to stop game out of waiting next answer state"""
        results_dict = {creator_1.name: "-100"}
        req_message = MessageHelper.quiz_ended_on_stop(name=creator_1.name, results=results_dict)

        await store.bots_manager.handle_update(update=stop_game_update)
        assert store.vk_api.send_message.call_count == 9
        assert store.vk_api.send_message.mock_calls[8].kwargs["message"] == req_message

    async def test_stop_after_correct_answer(self, store, stop_game_update, creator_1, fill_db_with_questions,
                                             after_correct_answer_singleplayer_state):
        """Create 3x3 questions, start game session, run quiz, get chosen question, get correct answer, and then trying
        to stop game out of waiting next answer state"""
        results_dict = {creator_1.name: "100"}
        req_message = MessageHelper.quiz_ended_on_stop(name=creator_1.name, results=results_dict)

        await store.bots_manager.handle_update(update=stop_game_update)
        assert store.vk_api.send_message.call_count == 8
        assert store.vk_api.send_message.mock_calls[7].kwargs["message"] == req_message

    async def test_stop_after_stopping(self, store, stop_game_update, creator_1, fill_db_with_questions,
                                       start_game_update):
        """Create 3x3 questions, start game session, run quiz, get chosen question, get wrong answer, and then trying
        to stop game out of waiting next answer state"""
        results_dict = {creator_1.name: "100"}
        req_message = MessageHelper.no_session_to_stop

        await store.bots_manager.handle_update(update=stop_game_update)
        await store.bots_manager.handle_update(update=stop_game_update)
        assert store.vk_api.send_message.call_count == 2
        assert store.vk_api.send_message.mock_calls[1].kwargs["message"] == req_message